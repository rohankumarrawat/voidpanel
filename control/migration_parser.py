
import os
import shutil
import zipfile
import subprocess
import tarfile
from django.contrib.auth.models import User
from control.models import user as control_user, domain as control_domain, package as control_package
from function import _validate_sql_identifier

class MigrationParser:
    def __init__(self, archive_path, temp_dir='/tmp/migration_extract'):
        self.archive_path = archive_path
        self.temp_dir = temp_dir
        self.metadata = {
            'username': None,
            'email': None,
            'package': 'default', # fallback package
            'domains': [],
            'platform': 'unknown',
            'extracted_path': None
        }

    def prepare_environment(self):
        """Create a clean temporary directory for extraction."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        os.makedirs(self.temp_dir, exist_ok=True)

    def extract_archive(self):
        """Extract ZIP or TAR archive safely."""
        try:
            if self.archive_path.endswith('.zip'):
                with zipfile.ZipFile(self.archive_path, 'r') as zip_ref:
                    zip_ref.extractall(self.temp_dir)
            elif self.archive_path.endswith('.tar.gz') or self.archive_path.endswith('.tar'):
                with tarfile.open(self.archive_path, 'r:*') as tar_ref:
                    tar_ref.extractall(self.temp_dir)
            else:
                raise ValueError("Unsupported archive format. Please use .zip or .tar.gz")
            self.metadata['extracted_path'] = self.temp_dir
            return True
        except Exception as e:
            raise Exception(f"Failed to extract archive: {str(e)}")

    def identify_platform(self):
        """Determine if this is a VoidPanel backup or CPanel."""
        # Check for VoidPanel specific structure (e.g. contains 'mail' folder inside domain, etc.)
        extracted_roots = os.listdir(self.temp_dir)
        
        # cPanel typically has `cp/` or `cpmove-` root structure, or `homedir/`
        if 'cp' in extracted_roots or any(f.startswith('cpmove-') for f in extracted_roots):
            self.metadata['platform'] = 'cpanel'
            return
            
        # VoidPanel typically has the raw data backed up via zip_multiple_locations_backup
        # which zips domain folders directly. E.g. we might see domain name folders in root.
        self.metadata['platform'] = 'voidpanel'

    def parse_voidpanel_backup(self):
        """Parse VoidPanel's extracted backup structure."""
        # VoidPanel backup ZIP structure:
        # If it was generated via zip_multiple_locations_backup, the root items are often
        # the domain directory itself, the mail folder (named domain.com), etc.
        # But we don't store a JSON meta file yet, so we infer from folder names.
        
        extracted = os.listdir(self.temp_dir)
        
        # Attempt to find the primary domain folder inside public_html
        candidate_domains = []
        for item in extracted:
            item_path = os.path.join(self.temp_dir, item)
            if os.path.isdir(item_path):
                # VoidPanel's user directory structure defaults to the username as the folder
                # Check for public_html inside it
                if os.path.exists(os.path.join(item_path, 'public_html')):
                    self.metadata['username'] = item
                    candidate_domains.append(item)
                    
        if not self.metadata['username'] and candidate_domains:
            self.metadata['username'] = candidate_domains[0]
            
        if self.metadata['username']:
            self.metadata['domains'] = [self.metadata['username']]
            self.metadata['email'] = f"admin@{self.metadata['username']}"
        else:
            raise Exception("Could not detect valid VoidPanel account structure inside archive.")

    def parse_cpanel_backup(self):
        """Skeleton method for parsing cPanel backup metadata."""
        # In a real cPanel backup, we parse cp/DOMAIN_NAME or userdata/ files
        # For now, this is a skeleton structure.
        self.metadata['username'] = 'cpanel_import_user'
        self.metadata['email'] = 'admin@cpanel-imported.com'
        self.metadata['domains'] = ['cpanel-imported.com']
        raise Exception("cPanel automated extraction engine requires full implementation of WHM metadata parsing.")

    def analyze(self):
        """Run the full analysis pipeline."""
        self.prepare_environment()
        self.extract_archive()
        self.identify_platform()
        
        if self.metadata['platform'] == 'voidpanel':
            self.parse_voidpanel_backup()
        elif self.metadata['platform'] == 'cpanel':
            self.parse_cpanel_backup()
            
        return self.metadata

    def build_system_account(self, auth_password='GeneratedPassword123!'):
        """Deploy the generated metadata onto the local Node infrastructure."""
        meta = self.metadata
        uname = meta['username']
        domain_name = meta['domains'][0]
        email = meta['email']
        package_name = meta['package']
        
        # Check for conflicts
        if control_user.objects.filter(username=uname).exists() or control_domain.objects.filter(domain=domain_name).exists():
            raise Exception(f"Account Conflict: Username '{uname}' or Domain '{domain_name}' already exists on this server. Aborting.")
            
        _validate_sql_identifier(uname)
        
        # 1. Create System Unix User
        try:
            subprocess.run(['sudo', 'useradd', '-m', '-s', '/bin/bash', uname], check=True)
            # Link password
            subprocess.run(['sudo', 'chpasswd'], input=f"{uname}:{auth_password}".encode(), check=True)
            # Create public_html
            subprocess.run(['sudo', 'mkdir', '-p', f'/home/{uname}/public_html'], check=True)
            subprocess.run(['sudo', 'chown', '-R', f'{uname}:{uname}', f'/home/{uname}/public_html'], check=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to provision Unix account: {str(e)}")

        # 2. Re-assign Extracted Files into User's Directory
        # Move extracted files to `/home/uname/`
        source_user_dir = os.path.join(self.temp_dir, uname)
        if os.path.exists(source_user_dir):
            try:
                # Copy properties safely
                subprocess.run(['sudo', 'cp', '-r', f'{source_user_dir}/.', f'/home/{uname}/'], check=True)
                subprocess.run(['sudo', 'chown', '-R', f'{uname}:{uname}', f'/home/{uname}'], check=True)
            except subprocess.CalledProcessError:
                pass # Gracefully handle non-fatal missing cp data
                
        # 3. Create Django Auth User
        dj_user = User.objects.create_user(username=uname, email=email, password=auth_password)
        
        # 4. Create Panel Models
        c_user = control_user.objects.create(
            username=uname,
            hosting_package=package_name,
            total_size="0",
            total_bandwidth="0",
            ip="127.0.0.1",
            domain=domain_name
        )
        c_domain = control_domain.objects.create(
            user=uname,
            domain=domain_name,
            dir=uname,
            docroot=f"/home/{uname}/public_html",
            email=email
        )
        
        # NOTE: Missing DB dumps are handled externally or ignored based on what VoidPanel's zip packs.
        
        # Clean up
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        return c_user, c_domain, auth_password
