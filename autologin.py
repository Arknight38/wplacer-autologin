#!/usr/bin/env python3
"""
Enhanced Auto-Login Script with Better UX
Features:
- Colorful console output with progress bars
- Interactive browser sessions for phone verification
- Better error handling and user feedback
- Configuration wizard
- Real-time statistics dashboard
"""

from camoufox.sync_api import Camoufox
from playwright.sync_api import TimeoutError as PWTimeout
from browserforge.fingerprints import Screen
from stem import Signal
from stem.control import Controller
import time, sys, pathlib, requests, os, json, itertools, random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import threading
from queue import Queue
import argparse

# Color codes for better terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Enhanced logging setup
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Colors.OKBLUE,
        'INFO': Colors.OKGREEN,
        'WARNING': Colors.WARNING,
        'ERROR': Colors.FAIL,
        'CRITICAL': Colors.FAIL + Colors.BOLD,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        if color:
            record.levelname = f"{color}{record.levelname}{Colors.ENDC}"
        return super().format(record)

# Configure enhanced logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter())
logger.handlers = [handler]

# Constants
CONSENT_BTN_XPATH = '/html/body/div[2]/div[1]/div[2]/c-wiz/main/div[3]/div/div/div[2]/div/div/button'
STATE_FILE = "./data/data.json"
EMAILS_FILE = "./data/emails.txt"
PROXIES_FILE = "./data/proxies.txt"
CONFIG_FILE = "./data/config.json"
POST_URL = "http://127.0.0.1:80/user"
CTRL_HOST, CTRL_PORT = "127.0.0.1", 9051
SOCKS_HOST, SOCKS_PORT = "127.0.0.1", 9050

# Enhanced solver API endpoints
SOLVER_BASE_URL = "http://localhost:8080"
TURNSTILE_ENDPOINT = f"{SOLVER_BASE_URL}/turnstile"
RESULT_ENDPOINT = f"{SOLVER_BASE_URL}/result"
PHONE_BALANCE_ENDPOINT = f"{SOLVER_BASE_URL}/phone/balance"
PHONE_GET_ENDPOINT = f"{SOLVER_BASE_URL}/phone/get"
PHONE_SMS_ENDPOINT = f"{SOLVER_BASE_URL}/phone/sms"
PHONE_COMPLETE_ENDPOINT = f"{SOLVER_BASE_URL}/phone/complete"

class ProgressTracker:
    """Enhanced progress tracking with real-time statistics"""
    
    def __init__(self, total_accounts: int):
        self.total_accounts = total_accounts
        self.successful = 0
        self.failed = 0
        self.phone_verification_needed = 0
        self.start_time = time.time()
        self.current_account = 0
        
    def update(self, status: str, account_email: str = ""):
        self.current_account += 1
        if status == "success":
            self.successful += 1
        elif status == "error":
            self.failed += 1
        elif status == "phone_needed":
            self.phone_verification_needed += 1
            
        self.print_progress(account_email)
    
    def print_progress(self, current_email: str = ""):
        elapsed = time.time() - self.start_time
        remaining = self.total_accounts - self.current_account
        
        if self.current_account > 0:
            avg_time = elapsed / self.current_account
            eta = remaining * avg_time
            eta_str = str(timedelta(seconds=int(eta)))
        else:
            eta_str = "calculating..."
        
        # Create progress bar
        progress = self.current_account / self.total_accounts
        bar_length = 40
        filled_length = int(bar_length * progress)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Clear line and print progress
        print(f"\r{Colors.OKBLUE}Progress: [{bar}] {self.current_account}/{self.total_accounts} ({progress*100:.1f}%){Colors.ENDC}", end="")
        print(f"\n{Colors.OKGREEN}✅ Success: {self.successful}{Colors.ENDC} | {Colors.FAIL}❌ Failed: {self.failed}{Colors.ENDC} | {Colors.WARNING}📱 Phone needed: {self.phone_verification_needed}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}⏱️  ETA: {eta_str} | Current: {current_email[:30]}...{Colors.ENDC}")
        print("─" * 80)

class ConfigManager:
    """Manage script configuration with interactive setup"""
    
    @staticmethod
    def load_config() -> Dict:
        """Load configuration with defaults"""
        default_config = {
            "use_phone_verification": True,
            "max_retries_per_account": 3,
            "delay_between_accounts": (15, 30),
            "browser_timeout": 90,
            "interactive_browser_for_phone": True,
            "show_progress_bar": True,
            "auto_tor_renewal": True
        }
        
        if pathlib.Path(CONFIG_FILE).exists():
            try:
                with open(CONFIG_FILE, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Could not load config: {e}, using defaults")
        
        return default_config
    
    @staticmethod
    def save_config(config: Dict):
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save config: {e}")
    
    @staticmethod
    def interactive_setup() -> Dict:
        """Interactive configuration setup"""
        print(f"\n{Colors.HEADER}{'='*60}")
        print("🚀 Auto-Login Script Configuration Wizard")
        print(f"{'='*60}{Colors.ENDC}\n")
        
        config = ConfigManager.load_config()
        
        # Phone verification setting
        phone_choice = input(f"Enable phone verification? (y/n) [default: {'y' if config['use_phone_verification'] else 'n'}]: ").strip().lower()
        if phone_choice:
            config['use_phone_verification'] = phone_choice.startswith('y')
        
        # Max retries
        retry_input = input(f"Max retries per account [default: {config['max_retries_per_account']}]: ").strip()
        if retry_input.isdigit():
            config['max_retries_per_account'] = int(retry_input)
        
        # Interactive browser for phone verification
        if config['use_phone_verification']:
            interactive_choice = input(f"Open interactive browser for phone verification? (y/n) [default: {'y' if config['interactive_browser_for_phone'] else 'n'}]: ").strip().lower()
            if interactive_choice:
                config['interactive_browser_for_phone'] = interactive_choice.startswith('y')
        
        ConfigManager.save_config(config)
        
        print(f"\n{Colors.OKGREEN}✅ Configuration saved!{Colors.ENDC}\n")
        return config

class EnhancedPhoneVerificationHandler:
    """Enhanced phone verification with better error handling"""
    
    def __init__(self, service_code="go", country="1", max_wait_time=300):
        self.service_code = service_code
        self.country = country
        self.max_wait_time = max_wait_time
        self.session = requests.Session()
        self.session.timeout = 10
        self.balance_checked = False
        self.has_balance = False
    
    def check_balance(self) -> bool:
        """Check SMS service balance with caching"""
        if self.balance_checked:
            return self.has_balance
            
        try:
            logger.info(f"{Colors.OKCYAN}💰 Checking SMS service balance...{Colors.ENDC}")
            r = self.session.get(PHONE_BALANCE_ENDPOINT, timeout=10)
            if r.status_code == 200:
                data = r.json()
                balance = data.get("balance", 0.0)
                logger.info(f"{Colors.OKGREEN}💰 SMS Balance: ${balance:.2f}{Colors.ENDC}")
                self.has_balance = balance > 0
            elif r.status_code == 503:
                logger.warning(f"{Colors.WARNING}📱 Phone API not configured{Colors.ENDC}")
                self.has_balance = False
            else:
                logger.warning(f"{Colors.WARNING}⚠️  Balance check failed: {r.status_code}{Colors.ENDC}")
                self.has_balance = False
                
            self.balance_checked = True
            return self.has_balance
            
        except Exception as e:
            logger.warning(f"{Colors.WARNING}⚠️  Balance check error: {e}{Colors.ENDC}")
            self.balance_checked = True
            self.has_balance = False
            return False
    
    def get_phone_number(self) -> Tuple[Optional[str], Optional[str]]:
        """Get a phone number for verification with better logging"""
        try:
            logger.info(f"{Colors.OKCYAN}📱 Requesting phone number...{Colors.ENDC}")
            params = {"service": self.service_code, "country": self.country}
            r = self.session.get(PHONE_GET_ENDPOINT, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json()
                task_id = data.get("task_id")
                phone_number = data.get("phone_number")
                if task_id and phone_number:
                    logger.info(f"{Colors.OKGREEN}📱 Got phone: {phone_number}{Colors.ENDC}")
                    return task_id, phone_number
            logger.warning(f"{Colors.WARNING}❌ Failed to get phone: {r.status_code} - {r.text}{Colors.ENDC}")
            return None, None
        except Exception as e:
            logger.warning(f"{Colors.WARNING}❌ Phone request error: {e}{Colors.ENDC}")
            return None, None
    
    def wait_for_sms(self, task_id: str, timeout: Optional[int] = None) -> Optional[str]:
        """Wait for SMS code with enhanced progress tracking"""
        if timeout is None:
            timeout = self.max_wait_time
        
        start_time = time.time()
        logger.info(f"{Colors.OKCYAN}📨 Waiting for SMS code (timeout: {timeout}s)...{Colors.ENDC}")
        
        dots = 0
        while time.time() - start_time < timeout:
            try:
                params = {"task_id": task_id}
                r = self.session.get(PHONE_SMS_ENDPOINT, params=params, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") == "success":
                        sms_code = data.get("sms_code")
                        logger.info(f"{Colors.OKGREEN}📨 Received SMS code: {sms_code}{Colors.ENDC}")
                        return sms_code
                elif r.status_code == 202:
                    # Still waiting - show animated progress
                    elapsed = int(time.time() - start_time)
                    dots = (dots + 1) % 4
                    dot_str = "." * dots + " " * (3 - dots)
                    print(f"\r{Colors.OKCYAN}📨 Waiting for SMS{dot_str} ({elapsed}s/{timeout}s){Colors.ENDC}", end="")
                    time.sleep(2)
                    continue
                else:
                    logger.warning(f"{Colors.WARNING}❌ Error getting SMS: {r.status_code} - {r.text}{Colors.ENDC}")
                    break
                    
            except Exception as e:
                logger.debug(f"SMS check error: {e}")
                time.sleep(2)
        
        print()  # New line after progress dots
        logger.warning(f"{Colors.WARNING}⏰ Timeout waiting for SMS{Colors.ENDC}")
        return None
    
    def complete_verification(self, task_id: str, success: bool = True):
        """Mark phone verification as complete or cancelled"""
        try:
            params = {"task_id": task_id, "success": str(success).lower()}
            r = self.session.post(PHONE_COMPLETE_ENDPOINT, params=params, timeout=10)
            status = "completed" if success else "cancelled"
            if r.status_code == 200:
                logger.info(f"{Colors.OKGREEN}✅ Verification {status}{Colors.ENDC}")
            else:
                logger.warning(f"{Colors.WARNING}⚠️  Failed to mark as {status}: {r.status_code}{Colors.ENDC}")
        except Exception as e:
            logger.warning(f"{Colors.WARNING}⚠️  Completion error: {e}{Colors.ENDC}")

class InteractiveBrowserManager:
    """Manage interactive browser sessions for phone verification"""
    
    def __init__(self):
        self.pending_accounts = Queue()
        self.results = {}
    
    def add_account_for_verification(self, account_data: Dict):
        """Add account that needs phone verification"""
        self.pending_accounts.put(account_data)
    
    def open_interactive_browsers(self):
        """Open interactive browsers for all accounts needing phone verification"""
        if self.pending_accounts.empty():
            logger.info(f"{Colors.OKGREEN}🎉 No accounts need interactive phone verification!{Colors.ENDC}")
            return
        
        accounts_to_process = []
        while not self.pending_accounts.empty():
            accounts_to_process.append(self.pending_accounts.get())
        
        logger.info(f"{Colors.HEADER}{'='*80}")
        logger.info(f"🌐 Opening Interactive Browser Sessions")
        logger.info(f"Accounts needing phone verification: {len(accounts_to_process)}")
        logger.info(f"{'='*80}{Colors.ENDC}\n")
        
        for i, account_data in enumerate(accounts_to_process):
            email = account_data['email']
            logger.info(f"{Colors.OKBLUE}🌐 Opening browser {i+1}/{len(accounts_to_process)} for: {email}{Colors.ENDC}")
            
            try:
                self._open_single_interactive_browser(account_data)
            except Exception as e:
                logger.error(f"{Colors.FAIL}❌ Failed to open browser for {email}: {e}{Colors.ENDC}")
        
        logger.info(f"\n{Colors.OKGREEN}✅ All interactive browser sessions completed!{Colors.ENDC}")
    
    def _open_single_interactive_browser(self, account_data: Dict):
        """Open a single interactive browser session"""
        email = account_data['email']
        google_login_url = account_data['google_login_url']
        
        # Use no proxy for interactive sessions to avoid connection issues
        try:
            with Camoufox(
                headless=False,  # Interactive mode
                humanize=True,
                disable_coop=True,
                screen=Screen(max_width=1920, max_height=1080),
                fonts=["Arial", "Helvetica", "Times New Roman", "Verdana"],
                os=["windows", "macos", "linux"],
                geoip=True,
                i_know_what_im_doing=True
            ) as browser:
                page = browser.new_page()
                page.set_default_timeout(300000)  # 5 minute timeout for interactive
                
                logger.info(f"{Colors.OKCYAN}🌐 Navigate to Google login and complete verification manually{Colors.ENDC}")
                logger.info(f"{Colors.WARNING}👆 Browser will stay open - complete the login process manually{Colors.ENDC}")
                
                page.goto(google_login_url, wait_until="domcontentloaded")
                
                # Wait for user to complete login
                print(f"\n{Colors.HEADER}{'='*60}")
                print(f"🛠️  MANUAL VERIFICATION REQUIRED")
                print(f"{'='*60}{Colors.ENDC}")
                print(f"Account: {Colors.BOLD}{email}{Colors.ENDC}")
                print(f"Please complete the login process in the browser window.")
                print(f"Press Enter when finished (or 'skip' to skip this account):")
                
                user_input = input().strip().lower()
                
                if user_input == 'skip':
                    logger.info(f"{Colors.WARNING}⏭️  Skipped: {email}{Colors.ENDC}")
                    return
                
                # Try to extract cookie
                try:
                    cookie = None
                    for context in browser.contexts:
                        for c in context.cookies():
                            if c.get("name") == "j":
                                cookie = c
                                break
                        if cookie:
                            break
                    
                    if cookie:
                        logger.info(f"{Colors.OKGREEN}✅ Success: Cookie obtained for {email}{Colors.ENDC}")
                        self.results[email] = {'status': 'success', 'cookie': cookie}
                        
                        # Post to server
                        self._post_result_to_server(cookie)
                    else:
                        logger.warning(f"{Colors.WARNING}⚠️  No cookie found for {email}{Colors.ENDC}")
                        self.results[email] = {'status': 'no_cookie'}
                        
                except Exception as e:
                    logger.error(f"{Colors.FAIL}❌ Error extracting cookie for {email}: {e}{Colors.ENDC}")
                    self.results[email] = {'status': 'error', 'error': str(e)}
                
        except Exception as e:
            logger.error(f"{Colors.FAIL}❌ Browser error for {email}: {e}{Colors.ENDC}")
            self.results[email] = {'status': 'browser_error', 'error': str(e)}
    
    def _post_result_to_server(self, cookie: Dict):
        """Post successful result to server"""
        try:
            payload = {
                "cookies": {"j": cookie.get("value", "")},
                "expirationDate": 999999999
            }
            
            response = requests.post(POST_URL, json=payload, timeout=15)
            if response.status_code == 200:
                logger.info(f"{Colors.OKGREEN}📤 Result posted to server successfully{Colors.ENDC}")
            else:
                logger.warning(f"{Colors.WARNING}📤 Server post returned status {response.status_code}{Colors.ENDC}")
                
        except Exception as e:
            logger.warning(f"{Colors.WARNING}📤 Failed to post to server: {e}{Colors.ENDC}")

def print_banner():
    """Print colorful script banner"""
    banner = f"""
{Colors.HEADER}{'='*80}
🚀 Enhanced Auto-Login Script v2.0
{'='*80}{Colors.ENDC}
{Colors.OKCYAN}✨ Features:
• Beautiful progress tracking
• Interactive browser sessions for phone verification
• Smart error handling and retry logic
• Real-time statistics dashboard
• Configuration wizard{Colors.ENDC}
{Colors.HEADER}{'='*80}{Colors.ENDC}
"""
    print(banner)

def load_proxies(path=PROXIES_FILE):
    """Load proxy list with enhanced error handling"""
    p = pathlib.Path(path)
    if not p.exists():
        logger.error(f"{Colors.FAIL}❌ Proxies file not found: {path}{Colors.ENDC}")
        sys.exit(1)
    
    proxies = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split(":")
        if len(parts) == 2:
            proxies.append(f"http://{parts[0]}:{parts[1]}")
        else:
            logger.warning(f"{Colors.WARNING}⚠️  Skipping invalid proxy line: {ln}{Colors.ENDC}")
    
    if not proxies:
        logger.error(f"{Colors.FAIL}❌ No valid proxies found{Colors.ENDC}")
        sys.exit(1)
    
    logger.info(f"{Colors.OKGREEN}🌐 Loaded {len(proxies)} proxies{Colors.ENDC}")
    return itertools.cycle(proxies)

# Initialize proxy pool
proxy_pool = load_proxies()

def get_solved_token(target_url="https://backend.wplace.live", 
                    sitekey="0x4AAAAAABpHqZ-6i7uL0nmG", max_retries=3):
    """Enhanced captcha solver with better progress tracking"""
    
    for attempt in range(max_retries):
        proxy = next(proxy_pool)
        session = requests.Session()
        
        try:
            logger.info(f"{Colors.OKCYAN}🔐 CAPTCHA attempt {attempt + 1}/{max_retries} using proxy{Colors.ENDC}")
            
            params = {"url": target_url, "sitekey": sitekey}
            
            # Submit captcha task
            r = session.get(TURNSTILE_ENDPOINT, params=params, timeout=20)
            if r.status_code != 202:
                raise RuntimeError(f"Bad status {r.status_code}: {r.text}")
            
            task_id = r.json().get("task_id")
            if not task_id:
                raise RuntimeError("No task_id returned")
            
            logger.info(f"{Colors.OKBLUE}🔐 CAPTCHA task started: {task_id}{Colors.ENDC}")
            
            # Poll for result with animated progress
            wait_times = [2, 3, 4, 5, 5, 5, 5, 5, 5, 5] * 6
            start_time = time.time()
            
            for i, wait_time in enumerate(wait_times):
                time.sleep(wait_time)
                elapsed = int(time.time() - start_time)
                
                # Animated progress indicator
                spinner = "|/-\\"[i % 4]
                print(f"\r{Colors.OKCYAN}🔐 Solving CAPTCHA {spinner} ({elapsed}s){Colors.ENDC}", end="")
                
                try:
                    res = session.get(RESULT_ENDPOINT, params={"id": task_id}, timeout=15)
                    
                    if res.status_code == 200:
                        data = res.json()
                        if data.get("status") == "success":
                            token = data.get("value")
                            print()  # New line after spinner
                            logger.info(f"{Colors.OKGREEN}🔐 CAPTCHA solved in {elapsed}s{Colors.ENDC}")
                            return token
                        elif data.get("status") == "error":
                            raise RuntimeError(f"Solver error: {data.get('value')}")
                    elif res.status_code == 202:
                        continue
                    elif res.status_code == 404:
                        raise RuntimeError("Task not found or expired")
                    else:
                        raise RuntimeError(f"Unexpected status {res.status_code}: {res.text}")
                        
                except requests.RequestException as e:
                    logger.debug(f"Poll error: {e}")
                    time.sleep(2)
                    continue
            
            print()  # New line after spinner
            raise RuntimeError("CAPTCHA solving timed out")
            
        except Exception as e:
            logger.warning(f"{Colors.WARNING}⚠️  CAPTCHA attempt {attempt + 1} failed: {e}{Colors.ENDC}")
            if attempt < max_retries - 1:
                wait_time = random.uniform(10, 20)
                logger.info(f"{Colors.OKCYAN}⏳ Retrying in {wait_time:.1f}s...{Colors.ENDC}")
                time.sleep(wait_time)
            else:
                raise RuntimeError(f"All {max_retries} CAPTCHA attempts failed. Last error: {e}")
        finally:
            session.close()

def main():
    """Enhanced main function with better UX"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Enhanced Auto-Login Script')
    parser.add_argument('--config', action='store_true', help='Run configuration wizard')
    parser.add_argument('--interactive-only', action='store_true', help='Only run interactive browser sessions')
    parser.add_argument('--no-progress', action='store_true', help='Disable progress bar')
    args = parser.parse_args()
    
    print_banner()
    
    # Configuration wizard
    if args.config:
        config = ConfigManager.interactive_setup()
    else:
        config = ConfigManager.load_config()
        logger.info(f"{Colors.OKBLUE}📋 Loaded configuration (use --config to modify){Colors.ENDC}")
    
    # Load state and accounts
    from enhanced_autologin_core import (
        load_state, save_state, get_accounts_by_status, 
        process_account_enhanced, tor_newnym_cookie
    )
    
    state = load_state()
    total_accounts = len(state["accounts"])
    
    if args.interactive_only:
        # Only run interactive browser sessions
        logger.info(f"{Colors.HEADER}🌐 Interactive Browser Mode{Colors.ENDC}")
        browser_manager = InteractiveBrowserManager()
        
        # Add accounts that failed with phone verification
        phone_needed_accounts = [
            acc for acc in state["accounts"] 
            if acc.get("status") == "phone_needed" or 
               (acc.get("status") == "error" and "phone" in acc.get("last_error", "").lower())
        ]
        
        for acc in phone_needed_accounts:
            browser_manager.add_account_for_verification({
                'email': acc['email'],
                'google_login_url': f"https://accounts.google.com/signin"  # Simplified URL
            })
        
        browser_manager.open_interactive_browsers()
        return
    
    # Determine accounts to process
    to_process = get_accounts_by_status(state, {"pending", "error"})
    to_process = [
        i for i in to_process 
        if state["accounts"][i].get("tries", 0) < config["max_retries_per_account"]
    ]
    
    if not to_process:
        logger.info(f"{Colors.OKGREEN}🎉 No accounts to process!{Colors.ENDC}")
        return
    
    # Initialize progress tracker
    if not args.no_progress and config.get("show_progress_bar", True):
        progress = ProgressTracker(len(to_process))
    else:
        progress = None
    
    # Initialize browser manager for accounts needing phone verification
    browser_manager = InteractiveBrowserManager()
    
    logger.info(f"{Colors.OKBLUE}🚀 Processing {len(to_process)} accounts...{Colors.ENDC}")
    
    # Process accounts
    start_time = time.time()
    for i, idx in enumerate(to_process):
        acc = state["accounts"][idx]
        
        try:
            result = process_account_enhanced(state, idx, config, browser_manager)
            
            if progress:
                progress.update(result["status"], acc["email"])
            
            # Auto TOR renewal
            if config.get("auto_tor_renewal", True):
                tor_newnym_cookie()
            
            # Delay between accounts
            if i < len(to_process) - 1:  # Don't delay after the last account
                delay_range = config.get("delay_between_accounts", (15, 30))
                delay = random.uniform(delay_range[0], delay_range[1])
                logger.info(f"{Colors.OKCYAN}⏳ Waiting {delay:.1f}s before next account...{Colors.ENDC}")
                time.sleep(delay)
                
        except KeyboardInterrupt:
            logger.info(f"\n{Colors.WARNING}🛑 Interrupted by user{Colors.ENDC}")
            break
        except Exception as e:
            logger.error(f"{Colors.FAIL}💥 Unexpected error processing {acc['email']}: {e}{Colors.ENDC}")
            if progress:
                progress.update("error", acc["email"])
            continue
    
    # Final summary
    total_time = time.time() - start_time
    print_final_summary(state, total_time)
    
    # Open interactive browsers for accounts needing phone verification
    if config.get("interactive_browser_for_phone", True):
        print(f"\n{Colors.HEADER}{'='*80}")
        print("🌐 Opening Interactive Browser Sessions")
        print(f"{'='*80}{Colors.ENDC}")
        browser_manager.open_interactive_browsers()
    
    # Final state save
    state["cursor"]["next_index"] = total_accounts
    save_state(state)
    
    print(f"\n{Colors.OKGREEN}🎉 Script completed successfully!{Colors.ENDC}")

def print_final_summary(state, total_time):
    """Print enhanced final summary"""
    total_accounts = len(state["accounts"])
    ok_accounts = get_accounts_by_status(state, {"ok"})
    error_accounts = get_accounts_by_status(state, {"error"})
    pending_accounts = get_accounts_by_status(state, {"pending"})
    phone_needed = get_accounts_by_status(state, {"phone_needed"})
    
    print(f"\n{Colors.HEADER}{'='*80}")
    print("📊 FINAL SUMMARY")
    print(f"{'='*80}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}✅ Successful: {len(ok_accounts)}{Colors.ENDC}")
    print(f"{Colors.FAIL}❌ Failed: {len(error_accounts)}{Colors.ENDC}")
    print(f"{Colors.WARNING}📱 Phone verification needed: {len(phone_needed)}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}⏳ Pending: {len(pending_accounts)}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}📈 Total processed: {total_accounts - len(pending_accounts)}/{total_accounts}{Colors.ENDC}")
    print(f"{Colors.OKBLUE}⏱️  Total time: {total_time/60:.1f} minutes{Colors.ENDC}")
    if total_accounts - len(pending_accounts) > 0:
        avg_time = total_time / (total_accounts - len(pending_accounts))
        print(f"{Colors.OKBLUE}⚡ Average per account: {avg_time:.1f} seconds{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")

# Helper functions for the core functionality
def exists(fr_or_pg, sel, t=500):
    """Check if element exists with timeout"""
    try:
        fr_or_pg.locator(sel).first.wait_for(state="visible", timeout=t)
        return True
    except PWTimeout:
        return False

def find_login_frame(pg, _type, timeout_s=30):
    """Find login frame with enhanced error detection"""
    t0 = time.time()
    err = False
    while time.time() - t0 < timeout_s and not err:
        for fr in pg.frames:
            try:
                frame_url = str(fr.url).lower()
                if "recaptcha" in frame_url or "challenge" in frame_url:
                    logger.warning(f"{Colors.WARNING}🤖 Captcha challenge detected in frame{Colors.ENDC}")
                    err = True
                    break
                if fr.locator(_type).count():
                    return fr
            except Exception:
                pass
        time.sleep(0.5)
    if err:
        raise TimeoutError("Captcha shown during login")
    raise TimeoutError(f"Login frame with {_type} not found")

def click_consent_xpath(gpage, timeout_s=20):
    """Click consent button if present"""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            btn = gpage.locator(f'xpath={CONSENT_BTN_XPATH}').first
            btn.wait_for(state="visible", timeout=1000)
            btn.click()
            logger.info(f"{Colors.OKGREEN}✅ Consent button clicked{Colors.ENDC}")
            return True
        except Exception:
            pass
        time.sleep(0.5)
    logger.debug("No consent button found (this is normal)")
    return False

def poll_cookie_any_context(browser, name="j", timeout_s=180):
    """Poll for authentication cookie across all contexts"""
    t0 = time.time()
    dots = 0
    while time.time() - t0 < timeout_s:
        try:
            for ctx in browser.contexts:
                for c in ctx.cookies():
                    if c.get("name") == name:
                        return c
        except Exception:
            pass
        
        # Show progress dots
        elapsed = int(time.time() - t0)
        dots = (dots + 1) % 4
        dot_str = "." * dots + " " * (3 - dots)
        print(f"\r{Colors.OKCYAN}🍪 Waiting for cookie{dot_str} ({elapsed}s/{timeout_s}s){Colors.ENDC}", end="")
        time.sleep(1)
    
    print()  # New line after progress
    return None

def handle_phone_verification_enhanced(page, phone_handler, interactive_mode=False):
    """Enhanced phone verification handler"""
    try:
        logger.info(f"{Colors.OKCYAN}📱 Checking for phone verification requirement...{Colors.ENDC}")
        
        # Check if phone verification is required
        phone_selectors = [
            'input[type="tel"]',
            'input[placeholder*="phone"]', 'input[placeholder*="Phone"]',
            'input[id*="phone"]', 'input[name*="phone"]',
            'input[aria-label*="phone"]', 'input[aria-label*="Phone"]'
        ]
        
        phone_input = None
        for selector in phone_selectors:
            if exists(page, selector, 3000):
                phone_input = page.locator(selector).first
                logger.info(f"{Colors.WARNING}📱 Phone verification required{Colors.ENDC}")
                break
        
        if not phone_input:
            logger.info(f"{Colors.OKGREEN}✅ No phone verification needed{Colors.ENDC}")
            return {"success": True, "interactive_needed": False}
        
        if interactive_mode:
            logger.info(f"{Colors.WARNING}👆 Interactive mode: Handle phone verification manually{Colors.ENDC}")
            return {"success": False, "interactive_needed": True, "reason": "phone_verification_manual"}
        
        # Automated phone verification
        if not phone_handler or not phone_handler.check_balance():
            logger.warning(f"{Colors.WARNING}📱 No phone service available - marking for interactive mode{Colors.ENDC}")
            return {"success": False, "interactive_needed": True, "reason": "no_phone_service"}
        
        # Get phone number
        task_id, phone_number = phone_handler.get_phone_number()
        if not task_id or not phone_number:
            logger.error(f"{Colors.FAIL}❌ Failed to get phone number{Colors.ENDC}")
            return {"success": False, "interactive_needed": True, "reason": "phone_number_failed"}
        
        # Enter phone number
        phone_input.fill(phone_number)
        time.sleep(random.uniform(1, 2))
        
        # Look for and click next/continue button
        next_buttons = [
            'button:has-text("Next")', 'button:has-text("Continue")',
            'button:has-text("Send")', 'input[type="submit"]',
            '#identifierNext', '[data-continue-type="next"]', 'button[type="submit"]'
        ]
        
        clicked = False
        for btn_sel in next_buttons:
            if exists(page, btn_sel, 1500):
                page.locator(btn_sel).first.click()
                clicked = True
                logger.info(f"{Colors.OKGREEN}✅ Clicked: {btn_sel}{Colors.ENDC}")
                break
        
        if not clicked:
            logger.error(f"{Colors.FAIL}❌ Could not find next button after entering phone{Colors.ENDC}")
            phone_handler.complete_verification(task_id, False)
            return {"success": False, "interactive_needed": True, "reason": "next_button_not_found"}
        
        # Wait for SMS code
        sms_code = phone_handler.wait_for_sms(task_id, timeout=180)
        if not sms_code:
            phone_handler.complete_verification(task_id, False)
            return {"success": False, "interactive_needed": True, "reason": "sms_timeout"}
        
        # Wait for SMS code input field
        time.sleep(3)
        code_selectors = [
            'input[type="text"][maxlength="6"]', 'input[type="text"][maxlength="8"]',
            'input[placeholder*="code"]', 'input[placeholder*="Code"]',
            'input[id*="code"]', 'input[name*="code"]',
            'input[aria-label*="code"]', 'input[aria-label*="Code"]'
        ]
        
        code_input = None
        for selector in code_selectors:
            if exists(page, selector, 10000):
                code_input = page.locator(selector).first
                break
        
        if not code_input:
            logger.error(f"{Colors.FAIL}❌ Could not find SMS code input field{Colors.ENDC}")
            phone_handler.complete_verification(task_id, False)
            return {"success": False, "interactive_needed": True, "reason": "code_input_not_found"}
        
        # Enter SMS code
        code_input.fill(sms_code)
        time.sleep(random.uniform(1, 2))
        
        # Click verify button
        verify_buttons = [
            'button:has-text("Verify")', 'button:has-text("Continue")',
            'button:has-text("Next")', 'input[type="submit"]', 'button[type="submit"]'
        ]
        
        for btn_sel in verify_buttons:
            if exists(page, btn_sel, 1500):
                page.locator(btn_sel).first.click()
                logger.info(f"{Colors.OKGREEN}✅ Verification submitted{Colors.ENDC}")
                break
        
        # Mark as successful
        phone_handler.complete_verification(task_id, True)
        time.sleep(5)  # Wait for verification to process
        
        logger.info(f"{Colors.OKGREEN}✅ Phone verification completed successfully{Colors.ENDC}")
        return {"success": True, "interactive_needed": False}
        
    except Exception as e:
        logger.error(f"{Colors.FAIL}❌ Phone verification failed: {e}{Colors.ENDC}")
        if 'task_id' in locals() and phone_handler:
            phone_handler.complete_verification(task_id, False)
        return {"success": False, "interactive_needed": True, "reason": f"exception: {str(e)}"}

def login_once_enhanced(email, password, config, browser_manager=None):
    """Enhanced single login attempt with better UX"""
    
    phone_handler = None
    if config.get("use_phone_verification", True):
        phone_handler = EnhancedPhoneVerificationHandler()
        if not phone_handler.check_balance():
            logger.info(f"{Colors.WARNING}📱 Phone verification disabled (no balance/not configured){Colors.ENDC}")
            phone_handler = None
    
    # Step 1: Solve captcha and get token
    try:
        logger.info(f"{Colors.OKCYAN}🔐 Solving CAPTCHA for {email}...{Colors.ENDC}")
        token = get_solved_token()
    except Exception as e:
        raise RuntimeError(f"Captcha solving failed: {e}")
    
    backend_url = f"https://backend.wplace.live/auth/google?token={token}"
    
    # Step 2: Follow redirect via HTTP proxy
    proxy_http = next(proxy_pool)
    proxies = {"http": proxy_http, "https": proxy_http}
    
    session = requests.Session()
    try:
        logger.info(f"{Colors.OKCYAN}🌐 Following redirect...{Colors.ENDC}")
        r = session.get(backend_url, allow_redirects=True, proxies=proxies, timeout=20)
        google_login_url = r.url
        logger.info(f"{Colors.OKGREEN}✅ Got Google login URL{Colors.ENDC}")
    except Exception as e:
        raise RuntimeError(f"Failed to get Google login URL: {e}")
    finally:
        session.close()
    
    # Step 3: Browser login via TOR
    tor_proxy = {"server": f"socks5://{SOCKS_HOST}:{SOCKS_PORT}"}
    custom_fonts = ["Arial", "Helvetica", "Times New Roman", "Verdana"]
    
    try:
        timeout_ms = config.get("browser_timeout", 90) * 1000
        
        with Camoufox(
            headless=True,
            humanize=True,
            block_images=True,
            disable_coop=True,
            screen=Screen(max_width=1920, max_height=1080),
            proxy=tor_proxy,
            fonts=custom_fonts,
            os=["windows", "macos", "linux"],
            geoip=True,
            i_know_what_im_doing=True
        ) as browser:
            page = browser.new_page()
            page.set_default_timeout(timeout_ms)
            
            # Human-like delay
            time.sleep(random.uniform(2, 4))
            
            logger.info(f"{Colors.OKCYAN}🌐 Opening Google login page...{Colors.ENDC}")
            page.goto(google_login_url, wait_until="domcontentloaded")
            
            # Step 4: Handle email input
            logger.info(f"{Colors.OKCYAN}📧 Entering email...{Colors.ENDC}")
            fr = find_login_frame(page, 'input[type="email"]', timeout_s=30)
            fr.fill('input[type="email"]', email)
            time.sleep(random.uniform(1, 2))
            fr.locator('#identifierNext').click()
            
            # Wait for password field
            time.sleep(random.uniform(3, 5))
            logger.info(f"{Colors.OKCYAN}🔒 Entering password...{Colors.ENDC}")
            fr = find_login_frame(page, 'input[type="password"]', timeout_s=30)
            fr.fill('input[type="password"]', password)
            time.sleep(random.uniform(1, 2))
            fr.locator('#passwordNext').click()
            
            # Step 5: Enhanced phone verification handling
            time.sleep(random.uniform(3, 5))
            interactive_mode = config.get("interactive_browser_for_phone", True)
            phone_result = handle_phone_verification_enhanced(page, phone_handler, interactive_mode)
            
            if phone_result.get("interactive_needed") and browser_manager:
                logger.info(f"{Colors.WARNING}📱 Adding {email} to interactive browser queue{Colors.ENDC}")
                browser_manager.add_account_for_verification({
                    'email': email,
                    'google_login_url': google_login_url,
                    'reason': phone_result.get("reason", "phone_verification")
                })
                return {"status": "phone_needed", "reason": phone_result.get("reason")}
            
            # Step 6: Handle consent
            time.sleep(random.uniform(2, 4))
            click_consent_xpath(page, timeout_s=20)
            
            # Step 7: Wait for cookie
            logger.info(f"{Colors.OKCYAN}🍪 Waiting for authentication cookie...{Colors.ENDC}")
            cookie = poll_cookie_any_context(browser, name="j", timeout_s=180)
            
            if cookie:
                logger.info(f"{Colors.OKGREEN}✅ Login successful - cookie obtained{Colors.ENDC}")
                return {"status": "success", "cookie": cookie}
            else:
                raise RuntimeError("Authentication cookie not found")
                
    except Exception as e:
        raise RuntimeError(f"Browser login failed: {e}")

def parse_emails_file(path=EMAILS_FILE):
    """Parse emails file with enhanced error handling"""
    p = pathlib.Path(path)
    if not p.exists():
        logger.error(f"{Colors.FAIL}❌ File not found: {path}{Colors.ENDC}")
        sys.exit(1)
    
    pairs = []
    line_num = 0
    for ln in p.read_text(encoding="utf-8").splitlines():
        line_num += 1
        s = ln.strip()
        if not s or s.startswith("#") or "|" not in s:
            continue
        
        try:
            email, password = s.split("|", 1)
            email = email.strip()
            password = password.strip()
            if email and password:
                pairs.append((email, password))
            else:
                logger.warning(f"{Colors.WARNING}⚠️  Skipping empty credentials on line {line_num}{Colors.ENDC}")
        except ValueError:
            logger.warning(f"{Colors.WARNING}⚠️  Invalid format on line {line_num}: {ln}{Colors.ENDC}")
    
    if not pairs:
        logger.error(f"{Colors.FAIL}❌ No valid credentials found{Colors.ENDC}")
        sys.exit(1)
    
    logger.info(f"{Colors.OKGREEN}📧 Loaded {len(pairs)} email/password pairs{Colors.ENDC}")
    return pairs

def load_state():
    """Load state with enhanced structure"""
    if pathlib.Path(STATE_FILE).exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"{Colors.WARNING}⚠️  Could not load state file: {e}, creating new{Colors.ENDC}")
    
    pairs = parse_emails_file()
    return {
        "version": 2,
        "created": datetime.now().isoformat(),
        "config": {
            "socks_host": SOCKS_HOST,
            "socks_port": SOCKS_PORT,
            "ctrl_host": CTRL_HOST,
            "ctrl_port": CTRL_PORT
        },
        "cursor": {"next_index": 0},
        "statistics": {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "phone_needed": 0
        },
        "accounts": [
            {
                "email": e,
                "password": p,
                "status": "pending",
                "tries": 0,
                "last_error": "",
                "last_attempt": None,
                "result": None
            }
            for e, p in pairs
        ],
    }

def save_state(state):
    """Save state with backup"""
    try:
        # Create backup
        if pathlib.Path(STATE_FILE).exists():
            backup_file = f"{STATE_FILE}.backup"
            pathlib.Path(STATE_FILE).rename(backup_file)
        
        # Save new state
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, STATE_FILE)
        
    except Exception as e:
        logger.error(f"{Colors.FAIL}❌ Failed to save state: {e}{Colors.ENDC}")

def get_accounts_by_status(state, statuses):
    """Return account indices by status"""
    if isinstance(statuses, str):
        statuses = {statuses}
    elif isinstance(statuses, (list, tuple)):
        statuses = set(statuses)
    
    return [
        i for i, acc in enumerate(state["accounts"])
        if acc.get("status", "pending").lower() in statuses
    ]

def tor_newnym_cookie(host=CTRL_HOST, port=CTRL_PORT):
    """Request new TOR identity with enhanced logging"""
    try:
        with Controller.from_port(address=host, port=port) as c:
            c.authenticate()
            if not c.is_newnym_available():
                wait_time = c.get_newnym_wait()
                logger.info(f"{Colors.OKCYAN}🔄 TOR rate limit: waiting {wait_time}s{Colors.ENDC}")
                time.sleep(wait_time)
            c.signal(Signal.NEWNYM)
        logger.info(f"{Colors.OKGREEN}🔄 TOR: New identity requested{Colors.ENDC}")
        time.sleep(2)  # Give TOR time to establish new circuit
    except Exception as e:
        logger.warning(f"{Colors.WARNING}⚠️  TOR newnym failed: {e}{Colors.ENDC}")

def process_account_enhanced(state, idx, config, browser_manager=None):
    """Enhanced account processing with better error handling"""
    acc = state["accounts"][idx]
    state["cursor"]["next_index"] = idx
    save_state(state)
    acc["tries"] += 1
    acc["last_attempt"] = datetime.now().isoformat()
    
    logger.info(f"\n{Colors.HEADER}{'='*80}")
    logger.info(f"🔄 PROCESSING ACCOUNT {idx + 1}/{len(state['accounts'])}")
    logger.info(f"Email: {Colors.BOLD}{acc['email']}{Colors.ENDC}")
    logger.info(f"Attempt: {Colors.OKCYAN}{acc['tries']}{Colors.ENDC}")
    logger.info(f"Previous Status: {Colors.WARNING}{acc.get('status', 'pending')}{Colors.ENDC}")
    logger.info(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")
    
    start_time = time.time()
    
    try:
        # Attempt login
        result = login_once_enhanced(acc["email"], acc["password"], config, browser_manager)
        
        if result["status"] == "success":
            cookie = result["cookie"]
            
            # Post result to server
            payload = {
                "cookies": {"j": cookie.get("value", "")},
                "expirationDate": 999999999
            }
            
            post_session = requests.Session()
            try:
                post_response = post_session.post(POST_URL, json=payload, timeout=15)
                if post_response.status_code == 200:
                    logger.info(f"{Colors.OKGREEN}📤 Result posted to server successfully{Colors.ENDC}")
                else:
                    logger.warning(f"{Colors.WARNING}📤 Server post returned status {post_response.status_code}{Colors.ENDC}")
            except Exception as e:
                logger.warning(f"{Colors.WARNING}📤 Failed to post to server: {e}{Colors.ENDC}")
            finally:
                post_session.close()
            
            # Update state
            elapsed_time = time.time() - start_time
            acc["status"] = "ok"
            acc["last_error"] = ""
            acc["result"] = {
                "domain": cookie.get("domain", ""),
                "value": cookie.get("value", ""),
                "completion_time": elapsed_time,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"{Colors.OKGREEN}✅ SUCCESS: {acc['email']} (took {elapsed_time:.1f}s){Colors.ENDC}")
            return {"status": "success"}
            
        elif result["status"] == "phone_needed":
            acc["status"] = "phone_needed"
            acc["last_error"] = result.get("reason", "Phone verification required")
            logger.info(f"{Colors.WARNING}📱 PHONE NEEDED: {acc['email']} - {result.get('reason', '')}{Colors.ENDC}")
            return {"status": "phone_needed"}
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        error_msg = f"{type(e).__name__}: {e}"
        acc["status"] = "error"
        acc["last_error"] = error_msg
        
        logger.error(f"{Colors.FAIL}❌ FAILED: {acc['email']} | {error_msg} (took {elapsed_time:.1f}s){Colors.ENDC}")
        return {"status": "error", "error": error_msg}
        
    finally:
        save_state(state)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info(f"\n{Colors.WARNING}🛑 Script interrupted by user{Colors.ENDC}")
    except Exception as e:
        logger.error(f"{Colors.FAIL}💥 Script crashed: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()