#!/usr/bin/env python3
"""
Main Application Launcher
Unified interface for running all project scripts
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def colored_print(text, color=Colors.ENDC):
    """Print colored text"""
    print(f"{color}{text}{Colors.ENDC}")

def print_banner():
    """Print application banner"""
    banner = f"""
{Colors.HEADER}{'='*70}
    🚀 wplacer autologin launcher v1.0
{'='*70}{Colors.ENDC}

{Colors.OKCYAN}Enhanced Auto-Login Tool Suite{Colors.ENDC}
"""
    print(banner)

def check_file_exists(filename):
    """Check if a file exists and return status"""
    if os.path.exists(filename):
        return f"{Colors.OKGREEN}✅ Available{Colors.ENDC}"
    else:
        return f"{Colors.FAIL}❌ Missing{Colors.ENDC}"

def check_dependencies():
    """Check if required files and dependencies exist"""
    files_to_check = {
        'api_server.py': 'API Server',
        'autologin.py': 'Auto Login Tool',
        'convert_email_files.py': 'Email File Converter',
        'setup.py': 'Setup Script',
        'requirements.txt': 'Dependencies'
    }
    
    # Check for data files
    data_files = {
        'emails.txt': 'Account Data',
        'proxies.txt': 'Proxy List',
        'config.json': 'Configuration'
    }
    
    colored_print("\n📋 System Status Check:", Colors.BOLD)
    print("-" * 50)
    
    # Check core files
    colored_print("Core Files:", Colors.OKCYAN)
    all_core_good = True
    for filename, description in files_to_check.items():
        status = check_file_exists(filename)
        print(f"  {description:<20} : {status}")
        if "Missing" in status:
            all_core_good = False
    
    # Check data files
    colored_print("\nData Files:", Colors.OKCYAN)
    all_data_good = True
    for filename, description in data_files.items():
        status = check_file_exists(filename)
        print(f"  {description:<20} : {status}")
        if "Missing" in status:
            all_data_good = False
    
    print("-" * 50)
    
    if all_core_good:
        colored_print("✅ All core files present and ready!", Colors.OKGREEN)
    else:
        colored_print("⚠️  Some core files are missing. Some features may not work.", Colors.WARNING)
    
    if not all_data_good:
        colored_print("ℹ️  Some data files are missing. You may need to create them.", Colors.OKCYAN)
    
    return all_core_good

def run_script(script_name, description):
    """Run a Python script with error handling"""
    colored_print(f"\n🚀 Starting {description}...", Colors.OKBLUE)
    colored_print("="*60, Colors.OKBLUE)
    
    try:
        # Check if file exists
        if not os.path.exists(script_name):
            colored_print(f"❌ Error: {script_name} not found!", Colors.FAIL)
            return False
        
        # Run the script
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, 
                              text=True)
        
        if result.returncode == 0:
            colored_print(f"\n✅ {description} completed successfully!", Colors.OKGREEN)
        else:
            colored_print(f"\n⚠️  {description} exited with code {result.returncode}", Colors.WARNING)
        
        return True
        
    except KeyboardInterrupt:
        colored_print(f"\n❌ {description} interrupted by user", Colors.WARNING)
        return False
    except Exception as e:
        colored_print(f"\n❌ Error running {description}: {str(e)}", Colors.FAIL)
        return False

def install_requirements():
    """Install Python requirements"""
    if not os.path.exists('requirements.txt'):
        colored_print("❌ requirements.txt not found!", Colors.FAIL)
        return False
    
    colored_print("\n📦 Installing requirements...", Colors.OKBLUE)
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
                              capture_output=True, text=True)
        if result.returncode == 0:
            colored_print("✅ Requirements installed successfully!", Colors.OKGREEN)
            return True
        else:
            colored_print(f"❌ Failed to install requirements: {result.stderr}", Colors.FAIL)
            return False
    except Exception as e:
        colored_print(f"❌ Error installing requirements: {str(e)}", Colors.FAIL)
        return False

def run_setup():
    """Run the setup script"""
    if not os.path.exists('setup.py'):
        colored_print("❌ setup.py not found!", Colors.FAIL)
        return False
    
    colored_print("\n⚙️  Running setup...", Colors.OKBLUE)
    return run_script('setup.py', 'Setup Process')



def show_data_info():
    """Show information about data directory"""
    data_dir = 'data'
    if not os.path.exists(data_dir):
        colored_print("\n📁 Data directory not found", Colors.WARNING)
        colored_print("Would you like to create it? (y/n): ", Colors.OKCYAN, end="")
        if input().lower().startswith('y'):
            try:
                os.makedirs(data_dir, exist_ok=True)
                colored_print("✅ Data directory created successfully!", Colors.OKGREEN)
            except Exception as e:
                colored_print(f"❌ Failed to create directory: {str(e)}", Colors.FAIL)
        return
        
    colored_print("\n📁 Data Directory Contents:", Colors.OKBLUE)
    try:
        files = os.listdir(data_dir)
        if files:
            for i, file in enumerate(files[:10], 1):  # Show first 10 files
                file_path = os.path.join(data_dir, file)
                size = os.path.getsize(file_path) if os.path.isfile(file_path) else 0
                file_type = "📁 DIR" if os.path.isdir(file_path) else "📄 FILE"
                print(f"  {i:2}. {file_type} {file:<30} ({size} bytes)")
            
            if len(files) > 10:
                colored_print(f"     ... and {len(files)-10} more items", Colors.WARNING)
        else:
            colored_print("  📭 Directory is empty", Colors.WARNING)
    except PermissionError:
        colored_print("  ❌ Permission denied", Colors.FAIL)

def main_menu():
    """Display main menu and handle user selection"""
    while True:
        print("\n" + "="*70)
        colored_print("🎯 MAIN MENU", Colors.BOLD)
        print("="*70)
        
        menu_options = [
            ("1", "🔧 Run Setup", "setup.py"),
            ("2", "📦 Install Requirements", "requirements.txt"),
            ("3", "🌐 Start API Server", "api_server.py"),
            ("4", "🔐 Run Auto Login Tool", "autologin.py"),
            ("5", "📧 Convert Email Files", "convert_email_files.py"),
            ("6", "📁 Show Data Directory", "data/"),
            ("7", "🔍 System Status Check", "check"),
            ("8", "🚪 Exit", "exit")
        ]
        
        for option, description, _ in menu_options:
            print(f"  {Colors.OKCYAN}{option}{Colors.ENDC}. {description}")
        
        print("\n" + "-"*70)
        choice = input(f"{Colors.BOLD}Select option (1-8): {Colors.ENDC}").strip()
        
        if choice == "1":
            run_setup()
        elif choice == "2":
            install_requirements()
        elif choice == "3":
            colored_print("\n🌐 Starting API Server...", Colors.OKBLUE)
            colored_print("💡 Tip: Press Ctrl+C to stop the server", Colors.WARNING)
            run_script('api_server.py', 'API Server')
        elif choice == "4":
            run_script('autologin.py', 'Auto Login Tool')
        elif choice == "5":
            run_script('convert_email_files.py', 'Email File Converter')
        elif choice == "6":
            show_data_info()
        elif choice == "7":
            check_dependencies()
        elif choice == "8":
            colored_print("\n👋 Baiiii, thank you for using my toooollll!", Colors.OKGREEN)
            break
        else:
            colored_print(f"\n❌ Invalid choice '{choice}'. Please select 1-8.", Colors.FAIL)
        
        # Pause before showing menu again (except for exit)
        if choice != "9":
            input(f"\n{Colors.OKCYAN}Press Enter to continue...{Colors.ENDC}")

def startup_check():
    """Perform startup checks and show welcome message"""
    colored_print(f"\n🕐 Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", Colors.OKCYAN)
    colored_print(f"📂 Working directory: {os.getcwd()}", Colors.OKCYAN)
    colored_print(f"🐍 Python version: {sys.version.split()[0]}", Colors.OKCYAN)
    
    # Quick file check
    critical_files = ['api_server.py', 'autologin.py', 'convert_email_files.py', 'setup.py']
    missing_files = [f for f in critical_files if not os.path.exists(f)]
    
    if missing_files:
        colored_print(f"\n⚠️  Warning: Missing critical files: {', '.join(missing_files)}", Colors.WARNING)
        colored_print("Some features may not be available.", Colors.WARNING)
        colored_print("Run option 7 (System Status Check) for more details.", Colors.OKCYAN)

def main():
    """Main application entry point"""
    try:
        print_banner()
        startup_check()
        main_menu()
    except KeyboardInterrupt:
        colored_print(f"\n\n❌ Application interrupted by user. Goodbye! 👋", Colors.WARNING)
    except Exception as e:
        colored_print(f"\n💥 Unexpected error: {str(e)}", Colors.FAIL)
        sys.exit(1)

if __name__ == "__main__":
    main()