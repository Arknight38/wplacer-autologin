#!/usr/bin/env python3
"""
API Server for Turnstile Solver & Phone Number Services
Provides endpoints for captcha solving and phone verification
"""

import time
import uuid
import asyncio
import aiohttp
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException, Depends
from fastapi.responses import JSONResponse
from loguru import logger
from camoufox import DefaultAddons
from camoufox.async_api import AsyncCamoufox
import uvicorn
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import weakref

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


class PhoneAPIService(str, Enum):
    SMS_ACTIVATE = "sms-activate"
    FIVE_SIM = "5sim"
    SMS_MAN = "sms-man"


@dataclass
class PhoneResult:
    activation_id: str
    phone_number: str
    service: str
    start_time: float = field(default_factory=time.time)


@dataclass
class TurnstileResult:
    status: str
    start_time: float = field(default_factory=time.time)
    elapsed_time: Optional[float] = None
    value: Optional[str] = None
    message: Optional[str] = None


class PhoneNumberAPI:
    """Phone number API integration for SMS verification"""
    
    def __init__(self, service: PhoneAPIService, api_key: str):
        self.service = service
        self.api_key = api_key
        self.base_urls = {
            PhoneAPIService.SMS_ACTIVATE: "https://api.sms-activate.org/stubs/handler_api.php",
            PhoneAPIService.FIVE_SIM: "https://5sim.net/v1",
            PhoneAPIService.SMS_MAN: "http://api.sms-man.ru/control"
        }
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        await self.init_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close_session()
    
    async def init_session(self):
        """Initialize HTTP session with proper configuration"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={"User-Agent": "PhoneAPI/1.0"}
            )
    
    async def close_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_balance(self) -> float:
        """Get account balance"""
        if not self.session:
            await self.init_session()
        
        try:
            if self.service == PhoneAPIService.SMS_ACTIVATE:
                params = {
                    "api_key": self.api_key,
                    "action": "getBalance"
                }
                async with self.session.get(self.base_urls[self.service], params=params) as response:
                    response.raise_for_status()
                    result = await response.text()
                    if result.startswith("ACCESS_BALANCE:"):
                        return float(result.split(":")[1])
                    else:
                        raise ValueError(f"Unexpected response: {result}")
            
            elif self.service == PhoneAPIService.FIVE_SIM:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with self.session.get(f"{self.base_urls[self.service]}/user/profile", headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return float(data.get("balance", 0.0))
            
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise
    
    async def get_number(self, service_code: str, country: str = "0") -> Dict[str, Any]:
        """
        Get a phone number for verification
        service_code: Service identifier (e.g., 'go' for Google, 'tg' for Telegram)
        country: Country code (0 for any, 1 for Russia, etc.)
        """
        if not self.session:
            await self.init_session()
        
        try:
            if self.service == PhoneAPIService.SMS_ACTIVATE:
                params = {
                    "api_key": self.api_key,
                    "action": "getNumber",
                    "service": service_code,
                    "country": country
                }
                async with self.session.get(self.base_urls[self.service], params=params) as response:
                    response.raise_for_status()
                    result = await response.text()
                    if result.startswith("ACCESS_NUMBER:"):
                        parts = result.split(":")
                        return {
                            "success": True,
                            "activation_id": parts[1],
                            "phone_number": parts[2]
                        }
                    else:
                        return {"success": False, "error": result}
            
            elif self.service == PhoneAPIService.FIVE_SIM:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                url = f"{self.base_urls[self.service]}/user/buy/activation/{country}/{service_code}"
                async with self.session.post(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "activation_id": str(result["id"]),
                            "phone_number": result["phone"]
                        }
                    else:
                        error_data = await response.json()
                        return {"success": False, "error": error_data}
            
            return {"success": False, "error": "Unsupported service"}
        except Exception as e:
            logger.error(f"Failed to get number: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_sms(self, activation_id: str) -> Dict[str, Any]:
        """Get SMS code for activation"""
        if not self.session:
            await self.init_session()
        
        try:
            if self.service == PhoneAPIService.SMS_ACTIVATE:
                params = {
                    "api_key": self.api_key,
                    "action": "getStatus",
                    "id": activation_id
                }
                async with self.session.get(self.base_urls[self.service], params=params) as response:
                    response.raise_for_status()
                    result = await response.text()
                    if result.startswith("STATUS_OK:"):
                        return {
                            "success": True,
                            "code": result.split(":")[1]
                        }
                    elif result == "STATUS_WAIT_CODE":
                        return {"success": False, "status": "waiting"}
                    else:
                        return {"success": False, "error": result}
            
            elif self.service == PhoneAPIService.FIVE_SIM:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with self.session.get(f"{self.base_urls[self.service]}/user/check/{activation_id}", 
                                           headers=headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    if data.get("sms") and len(data["sms"]) > 0:
                        return {
                            "success": True,
                            "code": data["sms"][0]["code"]
                        }
                    else:
                        return {"success": False, "status": "waiting"}
            
            return {"success": False, "error": "Unsupported service"}
        except Exception as e:
            logger.error(f"Failed to get SMS: {e}")
            return {"success": False, "error": str(e)}
    
    async def set_status(self, activation_id: str, status: str = "6") -> bool:
        """
        Set activation status
        status codes: 1=ready, 3=request_another_sms, 6=complete, 8=cancel
        """
        if not self.session:
            await self.init_session()
        
        try:
            if self.service == PhoneAPIService.SMS_ACTIVATE:
                params = {
                    "api_key": self.api_key,
                    "action": "setStatus",
                    "status": status,
                    "id": activation_id
                }
                async with self.session.get(self.base_urls[self.service], params=params) as response:
                    response.raise_for_status()
                    result = await response.text()
                    return result == "ACCESS_ACTIVATION"
            
            elif self.service == PhoneAPIService.FIVE_SIM:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                status_map = {"6": "finish", "8": "cancel"}
                mapped_status = status_map.get(status, "finish")
                
                if mapped_status == "finish":
                    url = f"{self.base_urls[self.service]}/user/finish/{activation_id}"
                else:
                    url = f"{self.base_urls[self.service]}/user/cancel/{activation_id}"
                
                async with self.session.patch(url, headers=headers) as response:
                    return response.status == 200
            
            return False
        except Exception as e:
            logger.error(f"Failed to set status: {e}")
            return False


class TurnstileAPIServer:
    HTML_TEMPLATE = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Turnstile Solver</title>
        <script src="https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onloadTurnstileCallback" async defer></script>
    </head>
    <body>
        <p id="ip-display"></p>
    </body>
    </html>
    """

    def __init__(self, headless: bool = True, thread: int = 10, page_count: int = 1, 
                 proxy_support: bool = False, phone_api_service: Optional[str] = None, 
                 phone_api_key: Optional[str] = None):
        self.headless = headless
        self.thread_count = thread
        self.page_count = page_count
        self.proxy_support = proxy_support
        self.page_pool: asyncio.Queue = asyncio.Queue()
        self.browser_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-first-run",
            "--disable-extensions",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
        ]
        self.camoufox: Optional[AsyncCamoufox] = None
        self.browser = None
        self.results: Dict[str, TurnstileResult] = {}
        self.phone_results: Dict[str, PhoneResult] = {}
        self.proxies = []
        self.max_task_num = self.thread_count * self.page_count
        self.current_task_num = 0
        self._cleanup_task = None
        self._periodic_task = None
        
        # Initialize phone API if credentials provided
        self.phone_api: Optional[PhoneNumberAPI] = None
        if phone_api_service and phone_api_key:
            try:
                service_enum = PhoneAPIService(phone_api_service)
                self.phone_api = PhoneNumberAPI(service_enum, phone_api_key)
                logger.info(f"Phone API initialized: {phone_api_service}")
            except ValueError:
                logger.error(f"Invalid phone API service: {phone_api_service}")
                raise ValueError(f"Unsupported phone API service: {phone_api_service}")

    async def startup(self):
        """Initialize resources"""
        logger.info("Initializing browser and resources")
        try:
            await self._initialize_browser()
            if self.phone_api:
                await self.phone_api.init_session()
            
            # Start background tasks
            self._cleanup_task = asyncio.create_task(self._cleanup_results())
            self._periodic_task = asyncio.create_task(self._periodic_cleanup())
            
            logger.success("Server initialized successfully")
        except Exception as e:
            logger.error(f"Server initialization failed: {str(e)}")
            await self.shutdown()
            raise

    async def shutdown(self):
        """Clean up all resources"""
        logger.info("Shutting down server and cleaning up resources")
        
        # Cancel background tasks
        for task in [self._cleanup_task, self._periodic_task]:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Clean up browser resources
        if self.browser:
            try:
                # Close all pages and contexts
                while not self.page_pool.empty():
                    try:
                        page, context = self.page_pool.get_nowait()
                        await page.close()
                        await context.close()
                    except Exception as e:
                        logger.warning(f"Error closing page/context: {e}")
                
                await self.browser.close()
            except Exception as e:
                logger.warning(f"Browser cleanup error: {e}")
        
        # Clean up phone API
        if self.phone_api:
            try:
                await self.phone_api.close_session()
            except Exception as e:
                logger.warning(f"Phone API cleanup error: {e}")
        
        logger.success("Server shutdown completed")

    async def _cleanup_results(self):
        """Periodically clean up expired results"""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                current_time = time.time()
                
                # Clean turnstile results
                expired_turnstile = [
                    tid for tid, res in self.results.items()
                    if res.status == "error" and current_time - res.start_time > 3600
                ]
                for tid in expired_turnstile:
                    self.results.pop(tid, None)
                    logger.debug(f"Cleaned expired turnstile task: {tid}")
                
                # Clean phone results
                expired_phone = [
                    tid for tid, res in self.phone_results.items()
                    if current_time - res.start_time > 3600
                ]
                for tid in expired_phone:
                    self.phone_results.pop(tid, None)
                    logger.debug(f"Cleaned expired phone task: {tid}")
                
                if expired_turnstile or expired_phone:
                    logger.info(f"Cleaned {len(expired_turnstile)} turnstile and {len(expired_phone)} phone results")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")

    async def _periodic_cleanup(self, interval_minutes: int = 60):
        """Periodically recreate pages to prevent memory leaks"""
        while True:
            try:
                await asyncio.sleep(interval_minutes * 60)
                logger.info("Starting periodic page cleanup")

                total = self.page_pool.qsize()
                success = 0
                
                # Recreate all pages
                pages_to_recreate = []
                while not self.page_pool.empty():
                    try:
                        page, context = self.page_pool.get_nowait()
                        pages_to_recreate.append((page, context))
                    except asyncio.QueueEmpty:
                        break

                for page, context in pages_to_recreate:
                    try:
                        await page.close()
                        await context.close()
                    except Exception as e:
                        logger.warning(f"Error closing page/context: {e}")

                    try:
                        new_context = await self._create_context_with_proxy()
                        new_page = await new_context.new_page()
                        await self.page_pool.put((new_page, new_context))
                        success += 1
                        await asyncio.sleep(0.5)  # Rate limit page creation
                    except Exception as e:
                        logger.error(f"Error recreating page: {e}")

                logger.success(f"Page cleanup completed. Recreated {success}/{total} pages")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic cleanup error: {e}")

    async def _create_context_with_proxy(self, proxy: Optional[str] = None):
        """Create a new browser context with optional proxy"""
        if not proxy:
            return await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

        try:
            parts = proxy.split(':')
            if len(parts) == 2:
                # host:port
                return await self.browser.new_context(
                    proxy={"server": f"http://{proxy}"},
                    viewport={"width": 1920, "height": 1080}
                )
            elif len(parts) == 4:
                # host:port:user:pass
                host, port, user, password = parts
                return await self.browser.new_context(
                    proxy={
                        "server": f"http://{host}:{port}",
                        "username": user,
                        "password": password
                    },
                    viewport={"width": 1920, "height": 1080}
                )
            else:
                logger.warning(f"Invalid proxy format: {proxy}")
                return await self.browser.new_context()
        except Exception as e:
            logger.error(f"Error creating context with proxy {proxy}: {e}")
            return await self.browser.new_context()

    async def _initialize_browser(self):
        """Initialize the browser and page pool"""
        try:
            self.camoufox = AsyncCamoufox(
                headless=self.headless,
                exclude_addons=[DefaultAddons.UBO],
                args=self.browser_args
            )
            self.browser = await self.camoufox.start()

            # Create page pool
            for thread_idx in range(self.thread_count):
                context = await self._create_context_with_proxy()
                for page_idx in range(self.page_count):
                    page = await context.new_page()
                    await self.page_pool.put((page, context))
                    # Small delay to prevent overwhelming the browser
                    if thread_idx > 0 or page_idx > 0:
                        await asyncio.sleep(0.1)

            logger.success(f"Page pool initialized with {self.page_pool.qsize()} pages")
            
        except Exception as e:
            logger.error(f"Browser initialization failed: {e}")
            raise

    async def _solve_turnstile(self, task_id: str, url: str, sitekey: str, 
                              action: Optional[str] = None, cdata: Optional[str] = None):
        """Solve a Turnstile captcha"""
        start_time = time.time()
        
        try:
            page, context = await asyncio.wait_for(self.page_pool.get(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for available page - Task {task_id}")
            self.results[task_id] = TurnstileResult(
                status="error",
                start_time=start_time,
                elapsed_time=time.time() - start_time,
                value="no_page_available",
                message="No page available within timeout"
            )
            self.current_task_num -= 1
            return

        try:
            # Prepare URL and Turnstile HTML
            url_with_slash = url if url.endswith("/") else url + "/"
            turnstile_div = (
                f'<div class="cf-turnstile" style="background: white;" data-sitekey="{sitekey}"'
                + (f' data-action="{action}"' if action else '')
                + (f' data-cdata="{cdata}"' if cdata else '')
                + '></div>'
            )
            page_data = self.HTML_TEMPLATE.replace("<p id=\"ip-display\"></p>", turnstile_div)
            
            # Set up route and navigate
            await page.route(url_with_slash, lambda route: route.fulfill(body=page_data, status=200))
            await page.goto(url_with_slash, wait_until="networkidle", timeout=30000)
            
            # Resize turnstile element
            await page.eval_on_selector(
                "div.cf-turnstile", 
                "el => el.style.width = '70px'",
                timeout=5000
            )

            # Attempt to solve the captcha
            max_attempts = 60  # 30 seconds with 0.5s intervals
            for attempt in range(max_attempts):
                try:
                    turnstile_response = await page.input_value(
                        "[name=cf-turnstile-response]", 
                        timeout=1000
                    )
                    
                    if not turnstile_response:
                        # Click turnstile if no response yet
                        await page.locator("div.cf-turnstile").click(timeout=1000)
                        await asyncio.sleep(0.5)
                    else:
                        # Success!
                        elapsed_time = time.time() - start_time
                        self.results[task_id] = TurnstileResult(
                            status="success",
                            start_time=start_time,
                            elapsed_time=round(elapsed_time, 3),
                            value=turnstile_response
                        )
                        logger.info(f"Captcha solved successfully - Task {task_id}, Time: {elapsed_time:.3f}s")
                        return
                        
                except Exception as e:
                    logger.debug(f"Attempt {attempt + 1} failed for task {task_id}: {e}")
                    await asyncio.sleep(0.5)

            # If we get here, all attempts failed
            elapsed_time = time.time() - start_time
            self.results[task_id] = TurnstileResult(
                status="error",
                start_time=start_time,
                elapsed_time=round(elapsed_time, 3),
                value="timeout",
                message="Captcha solve timeout"
            )
            logger.warning(f"Captcha solve timeout - Task {task_id}, Time: {elapsed_time:.3f}s")

        except Exception as e:
            elapsed_time = time.time() - start_time
            self.results[task_id] = TurnstileResult(
                status="error",
                start_time=start_time,
                elapsed_time=round(elapsed_time, 3),
                value="captcha_fail",
                message=str(e)
            )
            logger.error(f"Captcha solve error - Task {task_id}: {e}")
        finally:
            self.current_task_num -= 1
            try:
                await self.page_pool.put((page, context))
            except Exception as e:
                logger.error(f"Error returning page to pool: {e}")

    # API Methods
    def get_phone_api_dependency(self):
        """Dependency to ensure phone API is available"""
        if not self.phone_api:
            raise HTTPException(status_code=503, detail="Phone API not configured")
        return self.phone_api

    async def get_phone_balance(self):
        """Get phone API balance"""
        phone_api = self.get_phone_api_dependency()
        try:
            balance = await phone_api.get_balance()
            return JSONResponse(
                content={"balance": balance, "status": "success"},
                status_code=200
            )
        except Exception as e:
            logger.error(f"Balance check failed: {e}")
            return JSONResponse(
                content={"status": "error", "message": str(e)},
                status_code=500
            )

    async def get_phone_number(self, service: str = Query(..., description="Service code (e.g., 'go' for Google)"), 
                              country: str = Query("0", description="Country code")):
        """Get a phone number for verification"""
        phone_api = self.get_phone_api_dependency()
        
        if not service.strip():
            raise HTTPException(status_code=400, detail="Service parameter cannot be empty")
        
        task_id = str(uuid.uuid4())
        try:
            result = await phone_api.get_number(service, country)
            
            if result["success"]:
                phone_result = PhoneResult(
                    activation_id=result["activation_id"],
                    phone_number=result["phone_number"],
                    service=service
                )
                self.phone_results[task_id] = phone_result
                
                logger.info(f"Phone number obtained: {result['phone_number']} (Task: {task_id})")
                
                return JSONResponse(
                    content={
                        "task_id": task_id,
                        "phone_number": result["phone_number"],
                        "status": "success"
                    },
                    status_code=200
                )
            else:
                return JSONResponse(
                    content={"status": "error", "message": result["error"]},
                    status_code=400
                )
        except Exception as e:
            logger.error(f"Phone number request failed: {e}")
            return JSONResponse(
                content={"status": "error", "message": str(e)},
                status_code=500
            )

    async def get_sms_code(self, task_id: str = Query(..., description="Task ID from phone number request")):
        """Get SMS code for phone verification"""
        phone_api = self.get_phone_api_dependency()
        
        if task_id not in self.phone_results:
            return JSONResponse(
                content={"status": "error", "message": "Invalid task_id or task expired"},
                status_code=404
            )
        
        phone_data = self.phone_results[task_id]
        try:
            result = await phone_api.get_sms(phone_data.activation_id)
            
            if result["success"]:
                return JSONResponse(
                    content={
                        "sms_code": result["code"],
                        "phone_number": phone_data.phone_number,
                        "status": "success"
                    },
                    status_code=200
                )
            elif result.get("status") == "waiting":
                return JSONResponse(
                    content={"status": "waiting", "message": "SMS not received yet"},
                    status_code=202
                )
            else:
                return JSONResponse(
                    content={"status": "error", "message": result.get("error", "Unknown error")},
                    status_code=400
                )
        except Exception as e:
            logger.error(f"SMS code request failed: {e}")
            return JSONResponse(
                content={"status": "error", "message": str(e)},
                status_code=500
            )

    async def complete_phone_verification(self, task_id: str = Query(..., description="Task ID"), 
                                        success: bool = Query(True, description="Whether verification succeeded")):
        """Mark phone verification as complete or cancel it"""
        phone_api = self.get_phone_api_dependency()
        
        if task_id not in self.phone_results:
            return JSONResponse(
                content={"status": "error", "message": "Invalid task_id or task expired"},
                status_code=404
            )
        
        phone_data = self.phone_results[task_id]
        try:
            status_code = "6" if success else "8"  # 6=complete, 8=cancel
            result = await phone_api.set_status(phone_data.activation_id, status_code)
            
            # Remove from results after completion
            self.phone_results.pop(task_id, None)
            
            action = "completed" if success else "cancelled"
            logger.info(f"Phone verification {action}: {phone_data.phone_number} (Task: {task_id})")
            
            return JSONResponse(
                content={"status": "success", "message": f"Verification {action}"},
                status_code=200
            )
        except Exception as e:
            logger.error(f"Phone verification completion failed: {e}")
            return JSONResponse(
                content={"status": "error", "message": str(e)},
                status_code=500
            )

    async def process_turnstile(self, 
                               url: str = Query(..., description="Target URL"),
                               sitekey: str = Query(..., description="Turnstile site key"),
                               action: Optional[str] = Query(None, description="Optional action parameter"),
                               cdata: Optional[str] = Query(None, description="Optional cdata parameter")):
        """Process a Turnstile captcha solving request"""
        
        # Validate inputs
        if not url.strip() or not sitekey.strip():
            raise HTTPException(
                status_code=400,
                detail="'url' and 'sitekey' parameters are required and cannot be empty"
            )

        if self.current_task_num >= self.max_task_num:
            logger.warning(f"Server at capacity - Current: {self.current_task_num}/{self.max_task_num}")
            return JSONResponse(
                content={"status": "error", "error": "Server at maximum capacity, please try again later"},
                status_code=429
            )

        task_id = str(uuid.uuid4())
        logger.info(f"New turnstile task - ID: {task_id}, URL: {url}, Sitekey: {sitekey[:20]}...")

        # Initialize task
        self.results[task_id] = TurnstileResult(
            status="process",
            message="solving captcha"
        )

        try:
            # Start solving task
            asyncio.create_task(self._solve_turnstile(task_id, url, sitekey, action, cdata))
            self.current_task_num += 1
            
            return JSONResponse(
                content={"task_id": task_id, "status": "accepted"},
                status_code=202
            )
        except Exception as e:
            logger.error(f"Error starting turnstile task {task_id}: {e}")
            self.results.pop(task_id, None)
            return JSONResponse(
                content={"status": "error", "message": f"Failed to start task: {str(e)}"},
                status_code=500
            )

    async def get_result(self, task_id: str = Query(..., alias="id", description="Task ID to get result for")):
        """Get the result of a Turnstile captcha solving task"""
        if not task_id.strip():
            return JSONResponse(
                content={"status": "error", "message": "Missing or empty task_id parameter"},
                status_code=400
            )

        if task_id not in self.results:
            return JSONResponse(
                content={"status": "error", "message": "Invalid task_id or task expired"},
                status_code=404
            )

        result = self.results[task_id]

        # Check for timeout on processing tasks
        if result.status == "process":
            if time.time() - result.start_time > 300:  # 5 minute timeout
                result.status = "error"
                result.elapsed_time = round(time.time() - result.start_time, 3)
                result.value = "timeout"
                result.message = "Task timeout after 5 minutes"
            else:
                # Still processing
                return JSONResponse(
                    content={
                        "status": result.status,
                        "message": result.message,
                        "elapsed_time": round(time.time() - result.start_time, 3)
                    },
                    status_code=202
                )

        # Remove completed task from results
        final_result = self.results.pop(task_id)

        # Determine appropriate status code
        if final_result.status == "success":
            status_code = 200
        elif final_result.value == "timeout":
            status_code = 408
        elif "captcha_fail" in str(final_result.value):
            status_code = 422
        else:
            status_code = 500

        response_data = {
            "status": final_result.status,
            "elapsed_time": final_result.elapsed_time
        }
        
        if final_result.value:
            response_data["value"] = final_result.value
        if final_result.message:
            response_data["message"] = final_result.message

        return JSONResponse(content=response_data, status_code=status_code)

    def get_server_status(self):
        """Get current server status and statistics"""
        return JSONResponse(
            content={
                "status": "running",
                "current_tasks": self.current_task_num,
                "max_tasks": self.max_task_num,
                "available_pages": self.page_pool.qsize(),
                "pending_turnstile_results": len(self.results),
                "pending_phone_results": len(self.phone_results),
                "phone_api_enabled": self.phone_api is not None
            },
            status_code=200
        )


# Application factory with proper lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    server = app.state.server
    await server.startup()
    try:
        yield
    finally:
        await server.shutdown()


def create_app(headless: bool = True, thread: int = 10, page_count: int = 1, 
               proxy_support: bool = False, phone_api_service: Optional[str] = None, 
               phone_api_key: Optional[str] = None) -> FastAPI:
    """Create FastAPI application with proper configuration"""
    
    # Create server instance
    server = TurnstileAPIServer(
        headless=headless,
        thread=thread,
        page_count=page_count,
        proxy_support=proxy_support,
        phone_api_service=phone_api_service,
        phone_api_key=phone_api_key
    )
    
    # Create FastAPI app with lifespan management
    app = FastAPI(
        title="Turnstile & Phone API Server",
        description="API server for solving Turnstile captchas and managing phone verifications",
        version="2.0.0",
        lifespan=lifespan
    )
    
    # Store server instance in app state
    app.state.server = server
    
    # Register routes
    app.get("/turnstile", 
           summary="Solve Turnstile Captcha", 
           description="Submit a Turnstile captcha for solving")(server.process_turnstile)
    
    app.get("/result", 
           summary="Get Turnstile Result", 
           description="Get the result of a Turnstile captcha solving task")(server.get_result)
    
    app.get("/status", 
           summary="Server Status", 
           description="Get current server status and statistics")(server.get_server_status)
    
    # Phone API routes (only if phone API is configured)
    if server.phone_api:
        app.get("/phone/balance", 
               summary="Get Phone API Balance", 
               description="Get current balance from phone number service")(server.get_phone_balance)
        
        app.get("/phone/get", 
               summary="Get Phone Number", 
               description="Request a phone number for verification")(server.get_phone_number)
        
        app.get("/phone/sms", 
               summary="Get SMS Code", 
               description="Get SMS verification code for a phone number")(server.get_sms_code)
        
        app.post("/phone/complete", 
                summary="Complete Phone Verification", 
                description="Mark phone verification as complete or cancelled")(server.complete_phone_verification)
    
    return app


if __name__ == '__main__':
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Turnstile & Phone API Server')
    parser.add_argument('--headless', action='store_true', default=True, help='Run browser in headless mode')
    parser.add_argument('--threads', type=int, default=10, help='Number of browser threads')
    parser.add_argument('--pages', type=int, default=1, help='Pages per thread')
    parser.add_argument('--proxy', action='store_true', default=False, help='Enable proxy support')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to')
    parser.add_argument('--phone-service', choices=['sms-activate', '5sim', 'sms-man'], 
                       help='Phone API service')
    parser.add_argument('--phone-key', help='Phone API key')
    
    args = parser.parse_args()
    
    # Get phone API config from environment variables if not provided via args
    phone_service = args.phone_service or os.getenv('PHONE_API_SERVICE')
    phone_key = args.phone_key or os.getenv('PHONE_API_KEY')
    
    if phone_service and not phone_key:
        logger.warning("Phone service specified but no API key provided")
        phone_service = None
    
    # Configure logging
    logger.remove()  # Remove default handler
    logger.add(
        lambda msg: print(msg, end=''),
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        level="INFO"
    )
    
    logger.info(f"Starting server with {args.threads} threads, {args.pages} pages per thread")
    if phone_service:
        logger.info(f"Phone API enabled: {phone_service}")
    
    try:
        app = create_app(
            headless=args.headless,
            thread=args.threads,
            page_count=args.pages,
            proxy_support=args.proxy,
            phone_api_service=phone_service,
            phone_api_key=phone_key
        )
        
        uvicorn.run(
            app, 
            host=args.host, 
            port=args.port,
            log_level="info",
            access_log=False  # Reduce noise in logs
        )
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        exit(1)