import json
import os
import re
import uuid
import shutil
import threading
import subprocess
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
try:
    from data.models import DeploymentProject, DeploymentBuild, DeploymentEnvVar
except Exception:
    from control.models import DeploymentProject, DeploymentBuild, DeploymentEnvVar

try:
    from data.models import domain, subdomainname
except Exception:
    try:
        from control.models import domain, subdomainname
    except Exception:
        domain = None
        subdomainname = None

try:
    from voidonyx.deployment_builder import is_subdomain_valid, run_project_build, DEPLOYMENTS_ROOT
except Exception:
    from control.deployment_builder import is_subdomain_valid, run_project_build, DEPLOYMENTS_ROOT



def get_or_set_guest_session(request):
    session_id = request.session.get('deploy_guest_id')
    if not session_id:
        session_id = f"guest_{uuid.uuid4().hex[:12]}"
        request.session['deploy_guest_id'] = session_id
    return session_id

def get_authenticated_user(request):
    """
    Robustly resolves authenticated user from request.user or session authentication keys.
    """
    user_obj = getattr(request, 'user', None)
    if user_obj and getattr(user_obj, 'is_authenticated', False):
        return user_obj

    session = getattr(request, 'session', None)
    if session:
        # 1. Standard Django session auth key
        user_id = session.get('_auth_user_id')
        if user_id:
            try:
                from django.contrib.auth.models import User
                u = User.objects.filter(id=user_id, is_active=True).first()
                if u: return u
            except Exception:
                pass

        # 2. Portal user id keys
        for key in ['user_id', 'uid', 'customer_id']:
            val = session.get(key)
            if val:
                try:
                    from django.contrib.auth.models import User
                    u = User.objects.filter(id=val, is_active=True).first()
                    if u: return u
                except Exception:
                    pass

        # 3. Username or email keys
        for key in ['username', 'user']:
            val = session.get(key)
            if val and isinstance(val, str):
                try:
                    from django.contrib.auth.models import User
                    u = User.objects.filter(username=val, is_active=True).first()
                    if u: return u
                except Exception:
                    pass

        email = session.get('email')
        if email and isinstance(email, str):
            try:
                from django.contrib.auth.models import User
                u = User.objects.filter(email__iexact=email, is_active=True).first()
                if u: return u
            except Exception:
                pass

    return None

def check_project_access(request, project):
    user_obj = get_authenticated_user(request)
    if user_obj and user_obj.is_authenticated:
        if project.user == user_obj or project.user_id == user_obj.id or getattr(user_obj, 'is_superuser', False):
            return True
    return False

def deployment_portal(request):
    """
    Renders the VoidOnyx Deployment Platform (Vercel-like dashboard).
    Only registered users can deploy and view their active applications.
    """
    user_obj = get_authenticated_user(request)
    is_auth = bool(user_obj and user_obj.is_authenticated)
    
    if is_auth:
        projects = DeploymentProject.objects.filter(user=user_obj).order_by('-updated_at')
    else:
        projects = DeploymentProject.objects.none()

    context = {
        'projects': projects,
        'user': user_obj,
        'is_authenticated': is_auth,
        'total_deployments': projects.count() if is_auth else 0,
        'active_deployments': projects.filter(status='live').count() if is_auth else 0,
    }
    return render(request, 'deploy/dashboard.html', context)


def api_check_subdomain(request):
    """
    GET /api/deploy/check-subdomain/?subdomain=<slug>
    Checks if a requested subdomain under *.voidonyx.com is available.
    """
    raw_subdomain = request.GET.get('subdomain', '').strip().lower()
    is_valid, res = is_subdomain_valid(raw_subdomain)
    
    if not is_valid:
        return JsonResponse({
            'available': False,
            'subdomain': raw_subdomain,
            'message': res
        })

    sub_slug = res
    full_dom = f"{sub_slug}.voidonyx.com"

    # 1. Check in DeploymentProject
    if DeploymentProject.objects.filter(subdomain=sub_slug).exists():
        return JsonResponse({
            'available': False,
            'subdomain': sub_slug,
            'full_domain': full_dom,
            'message': f"'{sub_slug}' is already taken. Please choose another."
        })

    # 2. Check in legacy VoidPanel domain / subdomain tables if available
    if domain and subdomainname:
        try:
            if domain.objects.filter(domain=full_dom).exists() or subdomainname.objects.filter(subdomain=full_dom).exists():
                return JsonResponse({
                    'available': False,
                    'subdomain': sub_slug,
                    'full_domain': full_dom,
                    'message': f"'{sub_slug}' is reserved by a VoidPanel account."
                })
        except Exception:
            pass

    return JsonResponse({
        'available': True,
        'subdomain': sub_slug,
        'full_domain': full_dom,
        'message': f"✓ {full_dom} is available!"
    })

def api_inspect_git_repo(request):
    """
    GET /deploy/api/inspect-git/?url=<git_repo_url>
    Inspects a remote git repo without full clone to automatically determine
    its default production branch (e.g. main or master).
    """
    url = request.GET.get('url', '').strip()
    if not url:
        return JsonResponse({'status': 'error', 'message': 'Git repository URL is required.'})

    if not (url.startswith('https://') or url.startswith('http://')):
        return JsonResponse({'status': 'error', 'message': 'Git URL must begin with https:// or http://'})

    detected_branch = 'main'
    try:
        proc = subprocess.run(
            ['git', 'ls-remote', '--symref', url, 'HEAD'],
            capture_output=True, text=True, timeout=8
        )
        if proc.returncode == 0:
            match = re.search(r'ref:\s+refs/heads/(\S+)\s+HEAD', proc.stdout)
            if match:
                detected_branch = match.group(1).strip()
                return JsonResponse({
                    'status': 'ok',
                    'default_branch': detected_branch,
                    'message': f"Auto-detected branch: {detected_branch}"
                })
    except Exception as e:
        pass

    return JsonResponse({
        'status': 'ok',
        'default_branch': detected_branch,
        'message': f"Default branch: {detected_branch}"
    })

@csrf_exempt
def api_create_deployment(request):
    """
    POST /api/deploy/create/
    Creates a new deployment project and initiates the ephemeral build.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = request.POST.dict()
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Invalid payload: {e}'}, status=400)

    name = data.get('name', '').strip()
    raw_subdomain = data.get('subdomain', '').strip().lower()
    source_type = data.get('source_type', 'git')
    git_repo = data.get('git_repo', '').strip()
    git_branch = data.get('git_branch', '').strip()
    framework = data.get('framework', 'auto')
    user_obj = get_authenticated_user(request)
    if not (user_obj and user_obj.is_authenticated):
        return JsonResponse({
            'status': 'error',
            'auth_required': True,
            'login_url': '/login/?next=/deploy/',
            'message': 'Only registered users can deploy applications. Please sign in or register to proceed.'
        }, status=401)

    is_admin = bool(user_obj and (getattr(user_obj, 'is_staff', False) or getattr(user_obj, 'is_superuser', False)))

    # Sanitize root_dir against traversal and command injection
    raw_root_dir = data.get('root_directory', '').strip()
    if raw_root_dir and not any(part in raw_root_dir for part in ['..', '~', '$', ';', '&', '|', '`', '\n']):
        root_dir = raw_root_dir.lstrip('/')
    else:
        root_dir = '/'

    # Restrict arbitrary shell commands to admin/staff users only
    if is_admin:
        install_cmd = data.get('install_command', '').strip()
        build_cmd = data.get('build_command', '').strip()
        start_cmd = data.get('start_command', '').strip()
        output_dir = data.get('output_directory', '').strip() or 'dist'
    else:
        # Non-admin users rely on safe automated builder presets
        install_cmd = ''
        build_cmd = ''
        start_cmd = ''
        output_dir = ''

    env_vars_data = data.get('env_vars', {})

    if not name:
        return JsonResponse({'status': 'error', 'message': 'Project name is required.'}, status=400)

    is_valid, sub_slug = is_subdomain_valid(raw_subdomain)
    if not is_valid:
        return JsonResponse({'status': 'error', 'message': sub_slug}, status=400)

    full_domain = f"{sub_slug}.voidonyx.com"

    # Check collision
    if DeploymentProject.objects.filter(subdomain=sub_slug).exists():
        return JsonResponse({'status': 'error', 'message': f"Subdomain '{sub_slug}' was just claimed. Please try another."}, status=409)

    # Automatic Branch Detection if not provided
    if source_type == 'git' and not git_branch:
        try:
            proc = subprocess.run(
                ['git', 'ls-remote', '--symref', git_repo, 'HEAD'],
                capture_output=True, text=True, timeout=8
            )
            if proc.returncode == 0:
                m = re.search(r'ref:\s+refs/heads/(\S+)\s+HEAD', proc.stdout)
                if m:
                    git_branch = m.group(1).strip()
        except Exception:
            pass
        if not git_branch:
            git_branch = 'main'

    # Create project
    project = DeploymentProject.objects.create(
        user=user_obj,
        guest_session_id='',
        name=name,
        subdomain=sub_slug,
        full_domain=full_domain,
        framework=framework,
        source_type=source_type,
        git_repo=git_repo if source_type == 'git' else '',
        git_branch=git_branch or 'main',
        root_directory=root_dir,
        install_command=install_cmd,
        build_command=build_cmd,
        start_command=start_cmd,
        output_directory=output_dir,
        status='queued'
    )

    # Store env vars if provided
    if isinstance(env_vars_data, dict):
        for k, v in env_vars_data.items():
            if k.strip():
                DeploymentEnvVar.objects.create(
                    project=project,
                    key=k.strip(),
                    value=str(v).strip()
                )

    # Create first build
    build = DeploymentBuild.objects.create(
        project=project,
        build_number=1,
        status='queued',
        build_logs=f"[{timezone.now().strftime('%H:%M:%S')}] Queued build #1 for {project.full_domain}\n"
    )

    # Trigger background build thread
    t = threading.Thread(target=run_project_build, args=(build,), daemon=True)
    t.start()

    return JsonResponse({
        'status': 'success',
        'success': True,
        'project_id': project.id,
        'build_id': build.id,
        'subdomain': project.subdomain,
        'full_domain': project.full_domain,
        'git_branch': project.git_branch,
        'message': f"Deployment queued for {project.full_domain}!"
    })

def api_build_status(request, build_id):
    """
    GET /api/deploy/build/<build_id>/status/
    Returns live terminal logs and status of a build.
    """
    try:
        build = DeploymentBuild.objects.select_related('project').get(id=build_id)
        return JsonResponse({
            'status': build.status,
            'project_status': build.project.status,
            'logs': build.build_logs,
            'duration': build.duration_seconds,
            'error': build.error_message,
            'full_domain': build.project.full_domain,
            'live_url': f"https://{build.project.full_domain}"
        })
    except DeploymentBuild.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Build not found'}, status=404)

@csrf_exempt
def api_redeploy(request, project_id):
    """
    POST /api/deploy/project/<project_id>/redeploy/
    Triggers a re-deploy for an existing project.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        project = DeploymentProject.objects.get(id=project_id)
        if not check_project_access(request, project):
            return JsonResponse({'error': 'Permission denied.'}, status=403)

        next_build_num = project.builds.count() + 1
        
        build = DeploymentBuild.objects.create(
            project=project,
            build_number=next_build_num,
            status='queued',
            build_logs=f"[{timezone.now().strftime('%H:%M:%S')}] Triggered re-deploy #{next_build_num}\n"
        )
        
        project.total_deploys += 1
        project.status = 'queued'
        project.save(update_fields=['total_deploys', 'status'])

        t = threading.Thread(target=run_project_build, args=(build,), daemon=True)
        t.start()

        return JsonResponse({
            'status': 'success',
            'build_id': build.id,
            'message': 'Re-deployment started!'
        })
    except DeploymentProject.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)

@csrf_exempt
def api_delete_project(request, project_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        project = DeploymentProject.objects.get(id=project_id)
        if not check_project_access(request, project):
            return JsonResponse({'error': 'Permission denied.'}, status=403)

        subdomain = project.subdomain

        # 1. Clean up PM2 process
        try:
            subprocess.run(['pm2', 'delete', f'deploy-{subdomain}'], capture_output=True, check=False)
        except Exception:
            pass

        # 2. Remove dedicated reverse proxy configuration if present
        vhost_available = f'/etc/nginx/sites-available/app-{subdomain}.voidonyx.com.conf'
        vhost_enabled = f'/etc/nginx/sites-enabled/app-{subdomain}.voidonyx.com.conf'
        for vh in [vhost_enabled, vhost_available]:
            if os.path.lexists(vh) or os.path.islink(vh):
                try:
                    os.remove(vh)
                except Exception:
                    pass
        try:
            subprocess.run(['nginx', '-s', 'reload'], capture_output=True, check=False)
        except Exception:
            pass

        # 3. Clean up deployment directory
        project_dir = os.path.join(DEPLOYMENTS_ROOT, subdomain)
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir, ignore_errors=True)

        project.delete()
        return JsonResponse({'success': True, 'message': 'Deployment deleted successfully.'})
    except DeploymentProject.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ═══════════════════════════════════════════════════════════════════════════════
# IN-BROWSER FILE MANAGER & VS CODE TYPE WEB STUDIO API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

def _get_project_dir_and_verify(request, project_id):
    project = DeploymentProject.objects.get(id=project_id)
    if not check_project_access(request, project):
        return None, None, "Permission denied."
    
    project_dir = os.path.join(DEPLOYMENTS_ROOT, project.subdomain)
    os.makedirs(project_dir, exist_ok=True)
    return project, project_dir, None

def _sanitize_path(project_dir, rel_path):
    """
    Prevents path traversal attacks by validating that resolved path is strictly
    inside project_dir.
    """
    clean_rel = rel_path.strip().lstrip('/\\')
    norm = os.path.normpath(os.path.join(project_dir, clean_rel))
    real_project_dir = os.path.realpath(project_dir)
    real_norm = os.path.realpath(norm)
    if not (real_norm == real_project_dir or real_norm.startswith(real_project_dir + os.sep)):
        return None, "Invalid path: Access denied outside project boundary."
    return norm, None

def api_project_files(request, project_id):
    """
    GET /deploy/api/project/<project_id>/files/
    Returns the file and folder tree of the deployment project.
    """
    try:
        project, project_dir, err = _get_project_dir_and_verify(request, project_id)
        if err:
            return JsonResponse({'status': 'error', 'message': err}, status=403)

        IGNORE_NAMES = {'.git', 'node_modules', '__pycache__', '.venv', '.DS_Store', '.cache'}

        def build_tree(current_dir, rel_prefix='', depth=0):
            if depth > 6:
                return []
            items = []
            try:
                entries = sorted(os.listdir(current_dir), key=lambda x: (not os.path.isdir(os.path.join(current_dir, x)), x.lower()))
            except Exception:
                return []

            for entry in entries:
                if entry in IGNORE_NAMES:
                    continue
                full_path = os.path.join(current_dir, entry)
                rel_path = os.path.join(rel_prefix, entry).replace('\\', '/')
                is_dir = os.path.isdir(full_path)
                
                ext = ''
                size = 0
                if not is_dir:
                    _, ext = os.path.splitext(entry)
                    ext = ext.lstrip('.').lower()
                    try:
                        size = os.path.getsize(full_path)
                    except Exception:
                        size = 0

                item = {
                    'name': entry,
                    'path': rel_path,
                    'is_dir': is_dir,
                    'ext': ext,
                    'size': size,
                }
                if is_dir:
                    item['children'] = build_tree(full_path, rel_path, depth + 1)
                items.append(item)
            return items

        file_tree = build_tree(project_dir)

        return JsonResponse({
            'status': 'ok',
            'project': {
                'id': project.id,
                'name': project.name,
                'subdomain': project.subdomain,
                'full_domain': project.full_domain,
                'framework': project.framework,
                'live_url': f"https://{project.full_domain}"
            },
            'files': file_tree
        })
    except DeploymentProject.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def api_project_get_file(request, project_id):
    """
    GET /deploy/api/project/<project_id>/get-file/?path=<rel_path>
    Retrieves UTF-8 text contents of a project file for the editor.
    """
    try:
        project, project_dir, err = _get_project_dir_and_verify(request, project_id)
        if err:
            return JsonResponse({'status': 'error', 'message': err}, status=403)

        rel_path = request.GET.get('path', '').strip()
        if not rel_path:
            return JsonResponse({'status': 'error', 'message': 'File path is required.'}, status=400)

        abs_path, path_err = _sanitize_path(project_dir, rel_path)
        if path_err:
            return JsonResponse({'status': 'error', 'message': path_err}, status=403)

        if not os.path.isfile(abs_path):
            return JsonResponse({'status': 'error', 'message': 'File does not exist or is a directory.'}, status=404)

        # File size guard (max 4MB for in-browser editing)
        file_size = os.path.getsize(abs_path)
        if file_size > 4 * 1024 * 1024:
            return JsonResponse({'status': 'error', 'message': 'File exceeds 4MB limit for browser editor.'}, status=400)

        with open(abs_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        _, ext = os.path.splitext(abs_path)
        ext = ext.lstrip('.').lower()

        return JsonResponse({
            'status': 'ok',
            'path': rel_path.replace('\\', '/'),
            'ext': ext,
            'content': content,
            'size': file_size
        })
    except DeploymentProject.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def api_project_save_file(request, project_id):
    """
    POST /deploy/api/project/<project_id>/save-file/
    Saves edited file content and syncs to live bundle if applicable.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        project, project_dir, err = _get_project_dir_and_verify(request, project_id)
        if err:
            return JsonResponse({'status': 'error', 'message': err}, status=403)

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            payload = request.POST.dict()

        rel_path = payload.get('path', '').strip()
        content = payload.get('content', '')

        if not rel_path:
            return JsonResponse({'status': 'error', 'message': 'File path is required.'}, status=400)

        abs_path, path_err = _sanitize_path(project_dir, rel_path)
        if path_err:
            return JsonResponse({'status': 'error', 'message': path_err}, status=403)

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Synchronize root index.html to dist/index.html if dist folder exists
        norm_rel = rel_path.replace('\\', '/').strip('/')
        if norm_rel == 'index.html':
            dist_index = os.path.join(project_dir, 'dist', 'index.html')
            os.makedirs(os.path.dirname(dist_index), exist_ok=True)
            with open(dist_index, 'w', encoding='utf-8') as df:
                df.write(content)

        # Keep permissions right
        try:
            subprocess.run(['chown', '-R', 'www-data:www-data', project_dir], check=False)
            subprocess.run(['chmod', '-R', '755', project_dir], check=False)
        except Exception:
            pass

        project.updated_at = timezone.now()
        project.save(update_fields=['updated_at'])

        return JsonResponse({
            'status': 'ok',
            'message': '✓ File saved successfully.',
            'path': norm_rel,
            'saved_at': timezone.now().strftime('%H:%M:%S')
        })
    except DeploymentProject.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Project not found'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def api_project_create_node(request, project_id):
    """
    POST /deploy/api/project/<project_id>/create-node/
    Creates a new file or directory inside the project workspace.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        project, project_dir, err = _get_project_dir_and_verify(request, project_id)
        if err:
            return JsonResponse({'status': 'error', 'message': err}, status=403)

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            payload = request.POST.dict()

        rel_path = payload.get('path', '').strip()
        node_type = payload.get('type', 'file').strip().lower()

        if not rel_path:
            return JsonResponse({'status': 'error', 'message': 'Path is required.'}, status=400)

        abs_path, path_err = _sanitize_path(project_dir, rel_path)
        if path_err:
            return JsonResponse({'status': 'error', 'message': path_err}, status=403)

        if node_type == 'dir':
            os.makedirs(abs_path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            if not os.path.exists(abs_path):
                with open(abs_path, 'w', encoding='utf-8') as f:
                    f.write('')

        subprocess.run(['chown', '-R', 'www-data:www-data', project_dir], check=False)
        return JsonResponse({'status': 'ok', 'message': f"Created {node_type} successfully."})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def api_project_delete_node(request, project_id):
    """
    POST /deploy/api/project/<project_id>/delete-node/
    Deletes a file or directory safely inside the project workspace.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        project, project_dir, err = _get_project_dir_and_verify(request, project_id)
        if err:
            return JsonResponse({'status': 'error', 'message': err}, status=403)

        try:
            payload = json.loads(request.body.decode('utf-8'))
        except Exception:
            payload = request.POST.dict()

        rel_path = payload.get('path', '').strip().replace('\\', '/').strip('/')
        if not rel_path or rel_path in ('.', 'dist'):
            return JsonResponse({'status': 'error', 'message': 'Cannot delete root directory or dist directory.'}, status=400)

        abs_path, path_err = _sanitize_path(project_dir, rel_path)
        if path_err:
            return JsonResponse({'status': 'error', 'message': path_err}, status=403)

        if not os.path.exists(abs_path):
            return JsonResponse({'status': 'error', 'message': 'Path does not exist.'}, status=404)

        if os.path.isdir(abs_path):
            shutil.rmtree(abs_path, ignore_errors=True)
        else:
            os.remove(abs_path)

        return JsonResponse({'status': 'ok', 'message': 'Deleted successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@csrf_exempt
def api_project_redeploy_live(request, project_id):
    """
    POST /deploy/api/project/<project_id>/redeploy-live/
    Instantly re-publishes the edited project files to the live serving dist directory.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    try:
        project, project_dir, err = _get_project_dir_and_verify(request, project_id)
        if err:
            return JsonResponse({'status': 'error', 'message': err}, status=403)

        dist_dir = os.path.join(project_dir, 'dist')
        os.makedirs(dist_dir, exist_ok=True)

        # If project has index.html at root, ensure it's in dist/
        root_index = os.path.join(project_dir, 'index.html')
        if os.path.exists(root_index):
            shutil.copy(root_index, os.path.join(dist_dir, 'index.html'))

        # If Django project with manage.py, run collectstatic if possible
        manage_py = os.path.join(project_dir, 'manage.py')
        if os.path.exists(manage_py):
            try:
                subprocess.run(
                    ['python3', 'manage.py', 'collectstatic', '--noinput'],
                    cwd=project_dir, capture_output=True, timeout=30
                )
            except Exception:
                pass

        # Restart backend daemon if active
        pm2_name = f'deploy-{project.subdomain}'
        meta_file = os.path.join(project_dir, 'voiddeploy.json')
        has_pm2 = False
        if os.path.exists(meta_file):
            try:
                with open(meta_file, 'r', encoding='utf-8') as mf:
                    meta = json.load(mf)
                    has_pm2 = meta.get('has_backend', False)
            except Exception:
                pass

        if has_pm2 or getattr(project, 'has_backend', False):
            try:
                subprocess.run(['pm2', 'restart', pm2_name], capture_output=True, check=False)
            except Exception:
                pass

        # Update ownership and permissions
        subprocess.run(['chown', '-R', 'www-data:www-data', project_dir], check=False)
        subprocess.run(['chmod', '-R', '755', project_dir], check=False)

        project.updated_at = timezone.now()
        project.save(update_fields=['updated_at'])

        return JsonResponse({
            'status': 'ok',
            'message': f"🚀 Live updates synced to https://{project.full_domain}",
            'live_url': f"https://{project.full_domain}"
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
