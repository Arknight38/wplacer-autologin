#!/usr/bin/env python3
"""
Setup script for Enhanced Auto-Login
Creates necessary files and directories, checks dependencies
"""

import os
import sys
import pathlib
import subprocess
import json
from typing import List

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    """Print setup banner"""
    banner = f"""
{Colors.HEADER}{'='*80}
🛠️  Enhanced Auto-Login Setup Wizard
{'='*80}{Colors.ENDC}
{Colors.OKCYAN}This script will help you set up the Enhanced Auto-Login tool.
It will check dependencies, create config files, and guide you through initial setup.{Colors.ENDC}
{Colors.HEADER}{'='*80}{Colors.ENDC}
"""
    print(banner)

def check_python_version():
    """Check if Python version is compatible"""
    print(f"{Colors.OKBLUE}🐍 Checking Python version...{Colors.ENDC}")
    
    if sys.version_info < (3, 8):
        print(f"{Colors.FAIL}❌ Python 3.8 or higher is required. Current version: {sys.version}{Colors.ENDC}")
        return False
    
    print(f"{Colors.OKGREEN}✅ Python version: {sys.version.split()[0]}{Colors.ENDC}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    print(f"\n{Colors.OKBLUE}📦 Checking dependencies...{Colors.ENDC}")
    
    required_packages = [
        "camoufox",
        "playwright", 
        "browserforge",
        "stem",
        "requests"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"{Colors.OKGREEN}✅ {package}{Colors.ENDC}")
        except ImportError:
            print(f"{Colors.FAIL}❌ {package}{Colors.ENDC}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n{Colors.WARNING}⚠️  Missing packages: {', '.join(missing_packages)}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}💡 Install them with: pip install {' '.join(missing_packages)}{Colors.ENDC}")
        
        install_choice = input(f"\n{Colors.OKBLUE}Would you like to install missing packages now? (y/n): {Colors.ENDC}").strip().lower()
        if install_choice.startswith('y'):
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
                print(f"{Colors.OKGREEN}✅ All packages installed successfully!{Colors.ENDC}")
                return True
            except subprocess.CalledProcessError:
                print(f"{Colors.FAIL}❌ Failed to install packages. Please install manually.{Colors.ENDC}")
                return False
        else:
            return False
    
    print(f"{Colors.OKGREEN}✅ All dependencies are installed!{Colors.ENDC}")
    return True

def create_config_files():
    """Create necessary configuration files"""
    print(f"\n{Colors.OKBLUE}📄 Creating configuration files...{Colors.ENDC}")
    
    files_to_create = {
        "config.json": {
            "use_phone_verification": True,
            "max_retries_per_account": 3,
            "delay_between_accounts": [15, 30],
            "browser_timeout": 90,
            "interactive_browser_for_phone": True,
            "show_progress_bar": True,
            "auto_tor_renewal": True,
            "solver_settings": {
                "max_retries": 3,
                "timeout": 300
            },
            "phone_verification": {
                "service_code": "go",
                "country": "1",
                "max_wait_time": 300
            },
            "logging": {
                "level": "INFO",
                "show_colors": True,
                "save_logs": False,
                "log_file": "autologin.log"
            }
        }
    }
    
    example_files = {
        "emails.txt": """# Email and password file format
# Each line should be: email|password
# Lines starting with # are comments and will be ignored
# 
# Example:
# user1@example.com|password123
# user2@gmail.com|mypassword456
# 
# Add your email/password combinations below:
""",
        
        "proxies.txt": """# HTTP Proxy list (one per line)
# Format: host:port
# Lines starting with # are comments
#
# Example:
# 192.168.1.1:8080
# proxy.example.com:3128
#
# Add your proxies below:
""",
        
        "README.md": f"""# Enhanced Auto-Login Tool

## Features
- 🎨 Beautiful colorful console output with progress bars
- 🌐 Interactive browser sessions for phone verification
- ⚙️ Configuration wizard for easy setup
- 📊 Real-time statistics and progress tracking
- 🔄 Smart retry logic with exponential backoff
- 📱 Automated and manual phone verification support
- 🛡️ Enhanced error handling and recovery

## Quick Start

1. **Setup**: Run the setup script first
   ```bash
   python setup.py
   ```

2. **Configuration**: Run the configuration wizard
   ```bash
   python enhanced_autologin.py --config
   ```

3. **Add your credentials**: Edit `emails.txt` with your email/password pairs
   ```
   user1@gmail.com|password123
   user2@example.com|mypassword456
   ```

4. **Add proxies**: Edit `proxies.txt` with your HTTP proxies
   ```
   192.168.1.1:8080
   proxy.example.com:3128
   ```

5. **Run the script**:
   ```bash
   python enhanced_autologin.py
   ```

## Command Line Options

- `--config`: Run configuration wizard
- `--interactive-only`: Only open browsers for phone verification
- `--no-progress`: Disable progress bar

## File Structure

- `enhanced_autologin.py` - Main script
- `config.json` - Configuration settings
- `emails.txt` - Email/password pairs
- `proxies.txt` - HTTP proxy list
- `data.json` - State file (auto-generated)

## Phone Verification

The script supports both automatic and interactive phone verification:

1. **Automatic**: Uses SMS service API (requires configuration)
2. **Interactive**: Opens browser windows for manual verification

## Requirements

- Python 3.8+
- TOR proxy running on localhost:9050
- CAPTCHA solver API on localhost:8080
- HTTP proxies for initial requests

## Troubleshooting

### Common Issues:

1. **TOR not running**: Make sure TOR is running on port 9050
2. **CAPTCHA solver offline**: Check if solver API is available on port 8080
3. **No proxies**: Add valid HTTP proxies to proxies.txt
4. **Phone verification fails**: Enable interactive mode in config

### Getting Help:

1. Check the console output for detailed error messages
2. Review the configuration in `config.json`
3. Enable debug logging in config for more details

## Configuration Options

### Main Settings:
- `use_phone_verification`: Enable/disable phone verification
- `max_retries_per_account`: How many times to retry failed accounts
- `interactive_browser_for_phone`: Open browsers for manual phone verification
- `browser_timeout`: Browser timeout in seconds

### Advanced Settings:
- `delay_between_accounts`: Random delay range between accounts
- `auto_tor_renewal`: Automatically get new TOR identity
- `show_progress_bar`: Show animated progress bar

## Example Usage

```bash
# Run with default settings
python enhanced_autologin.py

# Configure settings interactively
python enhanced_autologin.py --config

# Only open browsers for accounts needing phone verification
python enhanced_autologin.py --interactive-only

# Run without progress bar (useful for logging)
python enhanced_autologin.py --no-progress
```

## Safety Features

- Automatic backups of state file
- Graceful handling of interruptions (Ctrl+C)
- Smart retry logic to avoid rate limits
- Detailed logging for debugging
- Configuration validation

Enjoy using the Enhanced Auto-Login Tool! 🚀
"""
    }
    
    created_files = []
    
    # Create config.json
    config_path = pathlib.Path("config.json")
    if not config_path.exists():
        try:
            with open(config_path, 'w') as f:
                json.dump(files_to_create["config.json"], f, indent=2)
            print(f"{Colors.OKGREEN}✅ Created config.json{Colors.ENDC}")
            created_files.append("config.json")
        except Exception as e:
            print(f"{Colors.FAIL}❌ Failed to create config.json: {e}{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}⚠️  config.json already exists, skipping{Colors.ENDC}")
    
    # Create example files
    for filename, content in example_files.items():
        file_path = pathlib.Path(filename)
        if not file_path.exists():
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                print(f"{Colors.OKGREEN}✅ Created {filename}{Colors.ENDC}")
                created_files.append(filename)
            except Exception as e:
                print(f"{Colors.FAIL}❌ Failed to create {filename}: {e}{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}⚠️  {filename} already exists, skipping{Colors.ENDC}")
    
    return created_files

def check_services():
    """Check if required services are running"""
    print(f"\n{Colors.OKBLUE}🔍 Checking required services...{Colors.ENDC}")
    
    services = [
        ("TOR SOCKS Proxy", "127.0.0.1", 9050),
        ("TOR Control Port", "127.0.0.1", 9051),
        ("CAPTCHA Solver API", "127.0.0.1", 8080)
    ]
    
    import socket
    
    service_status = {}
    for service_name, host, port in services:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"{Colors.OKGREEN}✅ {service_name} ({host}:{port}){Colors.ENDC}")
                service_status[service_name] = True
            else:
                print(f"{Colors.FAIL}❌ {service_name} ({host}:{port}) - Not accessible{Colors.ENDC}")
                service_status[service_name] = False
                
        except Exception as e:
            print(f"{Colors.FAIL}❌ {service_name} ({host}:{port}) - Error: {e}{Colors.ENDC}")
            service_status[service_name] = False
    
    return service_status

def print_setup_summary(created_files, service_status):
    """Print setup completion summary"""
    print(f"\n{Colors.HEADER}{'='*80}")
    print("📋 Setup Summary")
    print(f"{'='*80}{Colors.ENDC}")
    
    print(f"\n{Colors.OKBLUE}📄 Files Created:{Colors.ENDC}")
    if created_files:
        for filename in created_files:
            print(f"  {Colors.OKGREEN}✅ {filename}{Colors.ENDC}")
    else:
        print(f"  {Colors.WARNING}⚠️  No new files created (all exist){Colors.ENDC}")
    
    print(f"\n{Colors.OKBLUE}🔍 Service Status:{Colors.ENDC}")
    all_services_ok = True
    for service_name, status in service_status.items():
        if status:
            print(f"  {Colors.OKGREEN}✅ {service_name}{Colors.ENDC}")
        else:
            print(f"  {Colors.FAIL}❌ {service_name}{Colors.ENDC}")
            all_services_ok = False
    
    print(f"\n{Colors.OKBLUE}📋 Next Steps:{Colors.ENDC}")
    
    if not all_services_ok:
        print(f"  {Colors.WARNING}1. Start missing services (TOR, CAPTCHA solver){Colors.ENDC}")
        print(f"  {Colors.OKCYAN}   - TOR: Start TOR daemon with SOCKS on port 9050{Colors.ENDC}")
        print(f"  {Colors.OKCYAN}   - CAPTCHA: Start your CAPTCHA solver API on port 8080{Colors.ENDC}")
    
    if "emails.txt" in created_files:
        print(f"  {Colors.WARNING}2. Add your email/password pairs to emails.txt{Colors.ENDC}")
    
    if "proxies.txt" in created_files:
        print(f"  {Colors.WARNING}3. Add HTTP proxies to proxies.txt{Colors.ENDC}")
    
    print(f"  {Colors.OKGREEN}4. Run configuration wizard: python enhanced_autologin.py --config{Colors.ENDC}")
    print(f"  {Colors.OKGREEN}5. Start the script: python enhanced_autologin.py{Colors.ENDC}")
    
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")

def interactive_file_setup():
    """Interactive setup for emails and proxies"""
    print(f"\n{Colors.OKBLUE}🔧 Interactive File Setup{Colors.ENDC}")
    
    # Email setup
    setup_emails = input(f"{Colors.OKCYAN}Would you like to add email/password pairs now? (y/n): {Colors.ENDC}").strip().lower()
    if setup_emails.startswith('y'):
        emails = []
        print(f"{Colors.OKBLUE}Enter email/password pairs (format: email|password). Press Enter with empty line to finish:{Colors.ENDC}")
        
        while True:
            entry = input("Email|Password: ").strip()
            if not entry:
                break
            if '|' not in entry:
                print(f"{Colors.WARNING}⚠️  Invalid format. Use: email|password{Colors.ENDC}")
                continue
            emails.append(entry)
        
        if emails:
            try:
                with open('emails.txt', 'a') as f:
                    f.write('\n# Added by setup wizard:\n')
                    for email in emails:
                        f.write(f"{email}\n")
                print(f"{Colors.OKGREEN}✅ Added {len(emails)} email/password pairs{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.FAIL}❌ Failed to save emails: {e}{Colors.ENDC}")
    
    # Proxy setup
    setup_proxies = input(f"{Colors.OKCYAN}Would you like to add HTTP proxies now? (y/n): {Colors.ENDC}").strip().lower()
    if setup_proxies.startswith('y'):
        proxies = []
        print(f"{Colors.OKBLUE}Enter HTTP proxies (format: host:port). Press Enter with empty line to finish:{Colors.ENDC}")
        
        while True:
            entry = input("Proxy (host:port): ").strip()
            if not entry:
                break
            if ':' not in entry:
                print(f"{Colors.WARNING}⚠️  Invalid format. Use: host:port{Colors.ENDC}")
                continue
            proxies.append(entry)
        
        if proxies:
            try:
                with open('proxies.txt', 'a') as f:
                    f.write('\n# Added by setup wizard:\n')
                    for proxy in proxies:
                        f.write(f"{proxy}\n")
                print(f"{Colors.OKGREEN}✅ Added {len(proxies)} proxies{Colors.ENDC}")
            except Exception as e:
                print(f"{Colors.FAIL}❌ Failed to save proxies: {e}{Colors.ENDC}")

def test_basic_functionality():
    """Test basic functionality"""
    print(f"\n{Colors.OKBLUE}🧪 Testing Basic Functionality...{Colors.ENDC}")
    
    try:
        # Test config loading
        with open('config.json', 'r') as f:
            config = json.load(f)
        print(f"{Colors.OKGREEN}✅ Configuration file valid{Colors.ENDC}")
        
        # Test imports
        try:
            from enhanced_autologin import Colors as ScriptColors, ConfigManager
            print(f"{Colors.OKGREEN}✅ Script imports successful{Colors.ENDC}")
        except ImportError as e:
            print(f"{Colors.WARNING}⚠️  Could not import script modules: {e}{Colors.ENDC}")
            print(f"{Colors.OKCYAN}   This is normal if enhanced_autologin.py is not in the same directory{Colors.ENDC}")
        
        return True
        
    except Exception as e:
        print(f"{Colors.FAIL}❌ Basic functionality test failed: {e}{Colors.ENDC}")
        return False

def main():
    """Main setup function"""
    print_banner()
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Check dependencies
    if not check_dependencies():
        print(f"\n{Colors.FAIL}❌ Setup failed due to missing dependencies{Colors.ENDC}")
        return False
    
    # Create config files
    created_files = create_config_files()
    
    # Check services
    service_status = check_services()
    
    # Interactive file setup
    interactive_choice = input(f"\n{Colors.OKCYAN}Would you like to add emails/proxies interactively? (y/n): {Colors.ENDC}").strip().lower()
    if interactive_choice.startswith('y'):
        interactive_file_setup()
    
    # Test basic functionality
    test_basic_functionality()
    
    # Print summary
    print_setup_summary(created_files, service_status)
    
    print(f"\n{Colors.OKGREEN}🎉 Setup completed! You're ready to use the Enhanced Auto-Login tool.{Colors.ENDC}")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}🛑 Setup interrupted by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print(f"{Colors.FAIL}💥 Setup failed with error: {e}{Colors.ENDC}")
        sys.exit(1)