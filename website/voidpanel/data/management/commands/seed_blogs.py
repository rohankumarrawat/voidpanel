"""
Management command: seed_blogs
Seeds the 4 legacy static blog posts into the BlogPost database.
Run once: python manage.py seed_blogs
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from data.models import BlogCategory, BlogPost


BLOG_POSTS = [
    {
        "title": "Industrializing Machine Learning",
        "slug": "industrializing-machine-learning",
        "category": "Technology",
        "tags": "machine learning, AI, automation, MLOps",
        "content": """
<p>Industrializing Machine Learning is about transforming AI scalability and impact—standardizing the way businesses deploy, manage, and scale machine learning models in production. As organizations increasingly rely on AI to make data-driven decisions, the challenge lies in deploying ML models that are robust, reproducible, and scalable.</p>

<h2>Need for Industrialized ML</h2>

<p>In today's AI-first world, businesses must shift from handling data manually to embracing AI automation. This transition enables greater scalability and efficiency—but it's not without challenges. Organizations need to build robust pipelines for data ingestion and automation that ensure accuracy, integrity, and reliability throughout the entire ML lifecycle.</p>

<h2>Key Aspects of Industrialized Machine Learning</h2>

<p>Industrializing ML involves several critical domains that work in concert:</p>

<ul>
  <li><strong>Establishing End-to-End Pipelines:</strong> Automating data collection, preprocessing, training, evaluation, and deployment in a single orchestrated workflow.</li>
  <li><strong>Data Governance and Quality:</strong> Ensuring data is accurate, labeled correctly, and stored securely in compliant databases.</li>
  <li><strong>Model Standardization and Reusability:</strong> Building model registries and versioned artifacts that can be reused across projects.</li>
  <li><strong>Scalable Infrastructure:</strong> Leveraging cloud platforms (AWS, GCP, Azure) to handle growing data volumes and model complexity.</li>
  <li><strong>Continuous Integration and Deployment (CI/CD):</strong> Automating model retraining, testing, and rollout—similar to software DevOps practices.</li>
  <li><strong>Monitoring and Maintenance:</strong> Tracking model performance, data drift, and concept drift in real-time to prevent silent failures.</li>
  <li><strong>Compliance and Ethical AI:</strong> Ensuring models are fair, interpretable, and meet regulatory standards in healthcare, finance, and other regulated sectors.</li>
</ul>

<h2>Conclusion</h2>

<p>Industrializing Machine Learning is no longer a luxury—it's a necessity for businesses that want to remain competitive in a data-driven world. By adopting structured MLOps practices, organizations unlock the full potential of their AI investments, making systems sustainable, effective, and aligned with business goals.</p>
""",
        "date": "2024-11-20",
    },
    {
        "title": "The Power of Cloud Computing",
        "slug": "the-power-of-cloud-computing",
        "category": "Cloud",
        "tags": "cloud computing, AWS, Azure, IaaS, PaaS, SaaS",
        "content": """
<p>Cloud Computing has emerged as the game-changer in the modern era, where businesses and individuals demand more flexibility, scalability, and accessibility. This technological leap lets users access computing resources over the internet—eliminating the need for expensive physical infrastructure and local data silos.</p>

<h2>What is Cloud Computing?</h2>

<p>Cloud computing refers to delivering computing services—including storage, processing, networking, databases, and software—over the internet ("the cloud"). These services are hosted in globally distributed data centers managed by providers like Amazon Web Services (AWS), Microsoft Azure, and Google Cloud.</p>

<p>The core value: businesses can scale up or down on demand without heavy upfront investment. With pay-as-you-go pricing, organizations reduce TCO and eliminate hardware refresh cycles.</p>

<h2>How Does Cloud Computing Work?</h2>

<p>Cloud computing relies on a network of physical servers in data centers, interconnected via the internet. Data is stored in virtualized environments, enabling instant provisioning and elastic scaling. The underlying concept is <strong>virtualization</strong>—slicing physical resources into virtual units that can be allocated and reclaimed dynamically.</p>

<h2>Types of Cloud Services</h2>

<h3>Infrastructure as a Service (IaaS)</h3>
<p>Providers deliver virtualized computing resources over the internet. You lease virtual machines, storage, and networking—controlling the OS and applications while the provider manages the physical hardware. Examples: Amazon EC2, Google Compute Engine, Azure Virtual Machines.</p>

<h3>Platform as a Service (PaaS)</h3>
<p>PaaS provides a managed environment for developing, deploying, and scaling applications—abstracting the OS and infrastructure entirely. Developers focus purely on code. Examples: Google App Engine, Azure App Service, Heroku.</p>

<h3>Software as a Service (SaaS)</h3>
<p>Software delivered directly through the browser, with no local install required. Continuous updates, zero maintenance overhead. Examples: Google Workspace, Salesforce, Microsoft 365.</p>

<h3>Function as a Service (FaaS)</h3>
<p>Run discrete functions in response to events—no server management required. Billed per execution, ideal for microservices and event-driven architectures. Examples: AWS Lambda, Azure Functions, Google Cloud Functions.</p>

<h2>Benefits of Cloud Computing</h2>
<ul>
  <li><strong>Cost Efficiency:</strong> Pay only for what you use. No capital expenditure on hardware.</li>
  <li><strong>Scalability:</strong> Scale resources up or down in minutes to match demand.</li>
  <li><strong>Reliability:</strong> Multi-region redundancy ensures 99.99%+ uptime SLAs.</li>
  <li><strong>Security:</strong> Enterprise-grade encryption, IAM, and compliance certifications (ISO, SOC2, HIPAA).</li>
  <li><strong>Accessibility and Collaboration:</strong> Access from anywhere, collaborate across geographies in real time.</li>
  <li><strong>Automatic Updates:</strong> Providers handle patching, upgrades, and security fixes automatically.</li>
</ul>

<h2>Conclusion</h2>
<p>Cloud computing has fundamentally changed how businesses interact with technology. Whether you're a startup reducing infrastructure costs or an enterprise scaling globally, the cloud offers unmatched flexibility and power. The future is cloud-native—and adopting it today means staying ahead of the digital transformation curve.</p>
""",
        "date": "2024-11-25",
    },
    {
        "title": "VoidPanel: The Best Alternative to cPanel",
        "slug": "voidpanel-best-alternative-to-cpanel",
        "category": "VoidPanel",
        "tags": "cPanel alternative, VoidPanel, web hosting, control panel, Linux hosting",
        "content": """
<p>Managing web hosting no longer has to involve the complexity of cPanel's sprawling interface or its rising licensing costs. <strong>VoidPanel</strong> is a next-generation, open-source hosting control panel built for ISPs, web hosts, and developers who demand performance, customizability, and simplicity.</p>

<h2>Why Hosting Providers Are Moving Away from cPanel</h2>

<p>cPanel has long dominated the web hosting space—but the landscape has shifted. Dramatic licensing price hikes in recent years have forced many hosting providers to reconsider their stack. For a company running hundreds of servers, costs can balloon into tens of thousands of dollars annually just for the control panel software.</p>

<p>Beyond cost, cPanel's monolithic architecture makes customization difficult. Operators are locked into a specific workflow, specific feature set, and a specific pricing model with little flexibility.</p>

<h2>Enter VoidPanel</h2>

<p>VoidPanel takes a radically different approach. Designed from the ground up with a modern Django backend and a clean, dark-themed UI, VoidPanel gives hosting operators full control of their stack without vendor lock-in.</p>

<h3>Key Features</h3>
<ul>
  <li><strong>Domain & Subdomain Management:</strong> Create and manage hosted domains and subdomains with automatic Nginx vHost generation.</li>
  <li><strong>One-Click SSL:</strong> Auto-provision Let's Encrypt certificates for any domain in seconds.</li>
  <li><strong>Database Wizard:</strong> Create and manage MySQL/PostgreSQL databases and users with a guided UI.</li>
  <li><strong>Multi-Server Support:</strong> Manage multiple physical or virtual servers from a single admin console.</li>
  <li><strong>Client Portal:</strong> A business-ready portal for your customers to manage services, invoices, and support tickets.</li>
  <li><strong>MERN & Django App Hosting:</strong> First-class support for modern application stacks alongside traditional LAMP.</li>
  <li><strong>Backup Manager:</strong> Scheduled and on-demand backups with real-time progress tracking.</li>
</ul>

<h2>VoidPanel vs. cPanel: A Comparison</h2>

<table>
  <thead>
    <tr><th>Feature</th><th>VoidPanel</th><th>cPanel</th></tr>
  </thead>
  <tbody>
    <tr><td>License Cost</td><td>Free / Open Source</td><td>$20–$45+/month per server</td></tr>
    <tr><td>UI Design</td><td>Modern, dark-themed, responsive</td><td>Dated, complex multi-pane</td></tr>
    <tr><td>Extensibility</td><td>Fully customizable (Django)</td><td>Plugin-based, limited</td></tr>
    <tr><td>Modern App Support</td><td>MERN, Django, Node.js</td><td>Primarily PHP/LAMP</td></tr>
    <tr><td>Multi-Server</td><td>Built-in</td><td>Requires WHM add-on</td></tr>
  </tbody>
</table>

<h2>Getting Started with VoidPanel</h2>

<p>VoidPanel is designed for rapid deployment. A single installation script auto-detects your OS, configures Nginx, sets up the Django service, and provisions the database—all in one step.</p>

<pre><code>curl -fsSL https://get.voidpanel.com | bash</code></pre>

<p>After installation, the admin panel is accessible at <code>https://your-server-ip:8000/super-admin/</code> and the client portal at <code>/portal/</code>.</p>

<h2>Conclusion</h2>

<p>VoidPanel isn't just trying to replicate cPanel—it reimagines what a modern hosting control panel should be. Built by developers who run hosting operations themselves, it's a tool that respects your time, your budget, and your customers. If you're looking for a serious, production-grade cPanel alternative, VoidPanel is worth deploying today.</p>
""",
        "date": "2024-12-01",
    },
    {
        "title": "VoidPanel Overview: Open Source Hosting Control Panel",
        "slug": "voidpanel-overview-open-source-hosting-control-panel",
        "category": "VoidPanel",
        "tags": "VoidPanel, open source, hosting, control panel, web server",
        "content": """
<p>VoidPanel is an open-source, Django-powered web hosting control panel designed for developers, hosting providers, and system administrators who need full control over their infrastructure without the complexity or cost of traditional hosting panels.</p>

<h2>What Makes VoidPanel Different?</h2>

<p>Most hosting control panels are black boxes—opaque systems with limited customizability and expensive licensing. VoidPanel takes the opposite approach: every component is modular, every workflow is transparent, and the entire codebase is open for inspection and modification.</p>

<h2>Core Architecture</h2>

<p>VoidPanel is built on a battle-tested stack:</p>
<ul>
  <li><strong>Backend:</strong> Python / Django with a RESTful API layer</li>
  <li><strong>Task Queue:</strong> Celery with Redis for asynchronous provisioning jobs</li>
  <li><strong>Web Server:</strong> Nginx (auto-configured per account)</li>
  <li><strong>Database:</strong> MariaDB / PostgreSQL</li>
  <li><strong>Frontend:</strong> Vanilla HTML/CSS/JS with a modern dark-mode design system</li>
</ul>

<h2>Feature Highlights</h2>

<h3>Account & Domain Management</h3>
<p>Operators can create hosting accounts, provision system users, configure Nginx vHosts, and manage DNS records—all from a single dashboard. Each account is isolated at the OS level for security.</p>

<h3>SSL Certificate Automation</h3>
<p>VoidPanel integrates directly with Let's Encrypt via certbot. Certificates are provisioned, renewed, and revoked automatically without manual SSH access.</p>

<h3>Live Chat Support System</h3>
<p>A built-in live chat module allows clients to initiate support sessions directly from the portal. Staff and admins are notified in real time via browser alerts and audio notifications. Chat transcripts are emailed to both parties upon session close.</p>

<h3>Billing & Invoicing</h3>
<p>VoidPanel includes a basic billing system with invoice generation, payment tracking, and client-facing invoice views—covering the basics for small to medium hosting operations.</p>

<h3>License Management</h3>
<p>Hosting providers can distribute VoidPanel licenses to their own clients, with each license tied to a specific server IP and validated via a built-in API.</p>

<h2>Installation</h2>

<p>VoidPanel supports Ubuntu 20.04+, Debian 11+, and CentOS 8+. The installer script handles all dependencies:</p>

<pre><code># One-line installer
curl -fsSL https://get.voidpanel.com/install.sh | sudo bash

# Or with OS-specific scripts:
# For Ubuntu/Debian:
sudo bash install_ubuntu.sh

# For CentOS/RHEL:
sudo bash install_centos.sh</code></pre>

<h2>Roadmap</h2>

<p>The VoidPanel team is actively developing the following features:</p>
<ul>
  <li>Firewall Management UI with UFW/iptables integration</li>
  <li>Email server provisioning (Postfix/Dovecot)</li>
  <li>Advanced monitoring and alerting (resource usage, uptime)</li>
  <li>WordPress one-click installer</li>
  <li>Multi-language UI support</li>
</ul>

<h2>Conclusion</h2>

<p>VoidPanel is designed to grow with your hosting operation—from a single VPS to a multi-server fleet. Whether you're running a boutique hosting company or managing internal infrastructure, VoidPanel gives you the tools to do it efficiently and transparently.</p>

<p>Explore the source code, contribute to the project, or simply deploy it on your next server. The future of open hosting panels starts here.</p>
""",
        "date": "2024-12-10",
    },
]


class Command(BaseCommand):
    help = "Seed legacy static blog posts into the database"

    def handle(self, *args, **kwargs):
        # Get or create the superuser to be the author
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            self.stdout.write(self.style.ERROR("No superuser found. Create one first."))
            return

        seeded = 0
        skipped = 0

        for data in BLOG_POSTS:
            if BlogPost.objects.filter(slug=data["slug"]).exists():
                self.stdout.write(f"  Skipped (exists): {data['title']}")
                skipped += 1
                continue

            # Get or create category
            cat, _ = BlogCategory.objects.get_or_create(
                name=data["category"],
                defaults={"slug": data["category"].lower().replace(" ", "-")},
            )

            post = BlogPost(
                title=data["title"],
                slug=data["slug"],
                author=admin,
                category=cat,
                content=data["content"].strip(),
                tags=data["tags"],
                status="published",
                published_at=timezone.make_aware(
                    __import__("datetime").datetime.strptime(data["date"], "%Y-%m-%d")
                ),
            )
            post.save()
            seeded += 1
            self.stdout.write(self.style.SUCCESS(f"  Created: {data['title']}"))

        self.stdout.write(
            self.style.SUCCESS(f"\nDone! {seeded} posts created, {skipped} skipped.")
        )
