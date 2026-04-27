from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
import time
import re
from typing import Dict, List, Optional
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import webbrowser  # 用于打开作者链接

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager

    HAS_WEBDRIVER_MANAGER = True
except ImportError:
    HAS_WEBDRIVER_MANAGER = False
import os
import sys

def resource_path(relative_path):
    """
    获取资源文件的绝对路径。
    在开发环境中，返回相对路径；在 PyInstaller 打包后的环境中，
    返回临时文件夹 (sys._MEIPASS) 中的路径。
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包环境
        return os.path.join(sys._MEIPASS, relative_path)
    # 正常 Python 运行环境
    return os.path.join(os.path.abspath("."), relative_path)

class KeanCourseMonitor:
    def __init__(self, browser='edge', headless=False):
        self.driver = None
        self.browser = browser.lower()
        self.headless = headless
        self.is_authenticated = False
        self.base_url = "https://kean-ss.colleague.elluciancloud.com"
        self.schedule_url = f"{self.base_url}/Student/Planning/DegreePlans"

    def _init_driver(self):
        """初始化浏览器"""
        if self.driver:
            return

        try:
            if self.browser == 'edge':
                edge_options = EdgeOptions()
                if self.headless:
                    edge_options.add_argument('--headless')
                edge_options.add_argument('--no-sandbox')
                edge_options.add_argument('--disable-dev-shm-usage')
                edge_options.add_argument('--disable-blink-features=AutomationControlled')
                edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                edge_options.add_experimental_option('useAutomationExtension', False)
                edge_options.add_experimental_option("detach", True)

                print("正在初始化Edge浏览器...")
                if HAS_WEBDRIVER_MANAGER:
                    try:
                        print("尝试使用webdriver-manager...")
                        service = EdgeService(EdgeChromiumDriverManager().install())
                        self.driver = webdriver.Edge(service=service, options=edge_options)
                        print("✓ webdriver-manager初始化成功")
                        return
                    except Exception as e:
                        print(f"webdriver-manager失败: {e}")

                try:
                    print("尝试使用系统EdgeDriver...")
                    self.driver = webdriver.Edge(options=edge_options)
                    return
                except Exception as e:
                    print(f"系统EdgeDriver失败: {e}")
                    possible_paths = [
                        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedgedriver.exe",
                        r"C:\Windows\System32\msedgedriver.exe",
                        r"msedgedriver.exe"
                    ]
                    for path in possible_paths:
                        try:
                            service = EdgeService(executable_path=path)
                            self.driver = webdriver.Edge(service=service, options=edge_options)
                            return
                        except:
                            continue
                    raise Exception("无法找到EdgeDriver")

            else:  # Chrome
                chrome_options = ChromeOptions()
                if self.headless:
                    chrome_options.add_argument('--headless')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                chrome_options.add_experimental_option("detach", True)

                print("正在初始化Chrome浏览器...")
                if HAS_WEBDRIVER_MANAGER:
                    try:
                        service = ChromeService(ChromeDriverManager().install())
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                        return
                    except Exception as e:
                        print(f"webdriver-manager失败: {e}")

                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                    return
                except Exception as e:
                    raise Exception(f"无法找到ChromeDriver: {e}")

            if self.driver:
                self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined});'
                })

        except Exception as e:
            raise Exception(f"浏览器初始化失败: {str(e)}")

    def open_browser_and_wait_login(self) -> tuple[bool, str]:
        """打开浏览器并等待用户手动登录"""
        try:
            self._init_driver()
            print("🌐 打开登录页面...")
            self.driver.get(self.schedule_url)
            print("⏳ 等待你手动登录...")

            for i in range(120):  # 10分钟超时
                time.sleep(5)
                try:
                    current_url = self.driver.current_url
                    page_source = self.driver.page_source
                    login_success = False

                    if 'DegreePlans' in current_url or 'Planning/Courses' in current_url:
                        login_success = True
                    if 'Plan your Degree' in page_source or 'Schedule your courses' in page_source:
                        login_success = True

                    # 检查是否存在 Register Now 按钮 (作为登录成功的标志之一)
                    try:
                        if self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Register Now')]"):
                            login_success = True
                    except:
                        pass

                    if login_success:
                        time.sleep(2)
                        self.is_authenticated = True
                        print("\n✅ 登录成功!")
                        return True, "登录成功"

                except Exception:
                    pass

            return False, "等待登录超时(10分钟)"
        except Exception as e:
            return False, f"错误: {str(e)}"

    def check_login_status(self) -> bool:
        try:
            if 'okta.com' in self.driver.current_url: return False
            return True
        except:
            return False

    def switch_to_term(self, term_name: str) -> bool:
        """切换到指定学期 (极速版)"""
        try:
            if not self.check_login_status(): return False

            if 'DegreePlans' not in self.driver.current_url:
                self.driver.get(self.schedule_url)
                WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

            try:
                schedule_tab = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(text(), 'Schedule') or contains(text(), 'schedule')]"))
                )
                schedule_tab.click()
                time.sleep(0.5)
            except:
                pass

            target_parts = term_name.lower().split()
            required_keywords = [p for p in target_parts if p.isdigit() or p in ['fall', 'winter', 'spring', 'summer']]
            campus_keywords = [p for p in target_parts if p in ['wenzhou', 'union']]
            max_attempts = 25

            for attempt in range(max_attempts):
                try:
                    # 识别当前学期
                    term_text_elements = self.driver.find_elements(By.XPATH,
                                                                   "//h2 | //h3 | //div[contains(@class, 'term')] | //span[contains(@class, 'term')] | " +
                                                                   "//div[contains(@id, 'term')] | //*[contains(text(), '202')]")

                    found_match = False
                    for elem in term_text_elements:
                        if not elem.is_displayed(): continue
                        text = elem.text.strip().lower()
                        if len(text) < 5 or not any(y in text for y in ['2024', '2025', '2026', '2027']): continue

                        basic_match = all(k in text for k in required_keywords)
                        campus_match = True
                        if campus_keywords:
                            campus_match = all(k in text for k in campus_keywords)

                        if basic_match and campus_match:
                            found_match = True
                            break

                    if found_match:
                        time.sleep(0.5)
                        return True

                    # 点击下一个
                    next_button_selectors = [
                        "//button[@id='term-go-forward']", "//button[contains(@id, 'next-term')]",
                        "//button[contains(@aria-label, 'Next')]", "//button[@title='Next Term']",
                        "//button[.//span[contains(@class, 'chevron-right')]]",
                        "//button[.//i[contains(@class, 'right')]]", "//button[.//*[local-name()='svg']]",
                        "//button[contains(text(), '>')]"
                    ]

                    clicked = False
                    for selector in next_button_selectors:
                        try:
                            buttons = self.driver.find_elements(By.XPATH, selector)
                            for btn in buttons:
                                if btn.is_displayed() and btn.is_enabled():
                                    if any(x in btn.text.lower() for x in
                                           ['save', 'register', 'print', 'search']): continue
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                                    try:
                                        btn.click()
                                    except:
                                        self.driver.execute_script("arguments[0].click();", btn)
                                    clicked = True
                                    time.sleep(0.8)  # 翻页等待
                                    break
                            if clicked: break
                        except:
                            continue

                    if not clicked:
                        all_btns = self.driver.find_elements(By.TAG_NAME, "button")
                        for btn in all_btns:
                            if btn.is_displayed() and '<svg' in btn.get_attribute('innerHTML'):
                                loc = btn.location
                                if loc['y'] < 400 and loc['x'] > 200:
                                    try:
                                        btn.click()
                                        clicked = True
                                        time.sleep(0.8)
                                        break
                                    except:
                                        pass
                        if not clicked: return False

                except Exception:
                    time.sleep(0.5)
            return False
        except Exception:
            return False

    def attempt_registration(self) -> bool:
        """
        [新功能] 尝试点击页面上的 'Register Now' 按钮
        """
        try:
            # 查找 Register Now 按钮 (蓝色按钮, 通常在右上角)
            # 使用多个选择器确保能找到
            selectors = [
                "//button[contains(text(), 'Register Now')]",
                "//button[contains(text(), 'register now')]",
                "//button[contains(@aria-label, 'Register')]"
            ]

            target_btn = None
            for selector in selectors:
                btns = self.driver.find_elements(By.XPATH, selector)
                for btn in btns:
                    if btn.is_displayed() and btn.is_enabled():
                        target_btn = btn
                        break
                if target_btn: break

            if target_btn:
                # 滚动到可视区域
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", target_btn)
                time.sleep(0.2)

                # 点击
                try:
                    target_btn.click()
                except:
                    self.driver.execute_script("arguments[0].click();", target_btn)

                print("⚡ 已点击 Register Now 按钮!")
                return True
            else:
                print("⚠️ 未能在页面上找到 'Register Now' 按钮")
                return False

        except Exception as e:
            print(f"❌ 自动注册点击失败: {e}")
            return False

    def get_section_details(self, section_code: str, retry=2, skip_refresh=False) -> Optional[Dict]:
        """获取Section详情 (修复版)"""
        for attempt in range(retry):
            try:
                if attempt == 0:
                    if not skip_refresh:
                        self.driver.refresh()
                        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                        time.sleep(1.5)
                    else:
                        time.sleep(0.1)
                else:
                    time.sleep(1.5)

                section_selectors = [
                    f"//a[contains(text(), '{section_code}')]",
                    f"//div[contains(text(), '{section_code}')]",
                    f"//*[contains(text(), '{section_code}')]"
                ]

                section_element = None
                for selector in section_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for elem in elements:
                            if elem.is_displayed():
                                section_element = elem
                                break
                        if section_element: break
                    except:
                        continue

                if not section_element:
                    if attempt == retry - 1: print(f"❌ 找不到 {section_code}")
                    continue

                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", section_element)
                time.sleep(0.3)

                try:
                    section_element.click()
                except ElementClickInterceptedException:
                    self.driver.execute_script("arguments[0].click();", section_element)
                time.sleep(0.3)

                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Section Details')]")))
                    time.sleep(0.3)

                    dialog_text = ""
                    try:
                        dialog = self.driver.find_element(By.XPATH,
                                                          "//div[contains(@role, 'dialog') or contains(@class, 'modal')]")
                        dialog_text = dialog.text
                    except:
                        pass

                    if not dialog_text or len(dialog_text) < 50:
                        try:
                            dialog_text = self.driver.find_element(By.TAG_NAME, "body").text
                        except:
                            pass

                    if not dialog_text: continue

                    seats_patterns = [
                        r'Seats Available.*?(\d+)\s*/\s*(\d+)\s*/\s*(\d+)',
                        r'Seats Available.*?(\d+)\s*[/|]\s*(\d+)\s*[/|]\s*(\d+)',
                        r'Available\s*[:\s]*(\d+)\s*/\s*(\d+)\s*/\s*(\d+)'
                    ]

                    seats_match = None
                    for pattern in seats_patterns:
                        seats_match = re.search(pattern, dialog_text, re.I | re.DOTALL)
                        if seats_match: break

                    if seats_match:
                        available = int(seats_match.group(1))
                        capacity = int(seats_match.group(2))
                        waitlist = int(seats_match.group(3))

                        section_info = {
                            'code': section_code,
                            'available': available,
                            'capacity': capacity,
                            'waitlist': waitlist,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }

                        # 关闭弹窗
                        try:
                            close_button = self.driver.find_element(By.XPATH,
                                                                    "//button[contains(text(), 'Close') or contains(text(), '关闭') or contains(@aria-label, 'Close')]")
                            close_button.click()
                        except:
                            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)

                        time.sleep(0.5)
                        return section_info
                    else:
                        print(f"⚠️  未找到座位匹配信息")

                except TimeoutException:
                    pass
                except Exception:
                    pass
            except Exception:
                if attempt == retry - 1: pass

        return None

    def monitor_sections(self, term: str, sections: List[str], auto_register: bool = False, callback=None) -> Dict[
        str, Dict]:
        """监控多个sections (极速版 + 自动抢课)"""
        results = {}

        if not self.check_login_status():
            if callback: callback("❌ 登录失效")
            return results

        # 1. 刷新
        try:
            self.driver.refresh()
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(1.5)
        except Exception as e:
            if callback: callback(f"⚠️ 刷新超时: {e}")

        # 2. 切学期
        if not self.switch_to_term(term):
            if callback:
                callback(f"❌ 无法切换学期: {term}")
                callback("💡 请尝试手动切换")
            return results

        # 3. 获取数据
        for i, section in enumerate(sections):
            if callback:
                callback(f"\n{'=' * 30}")
                callback(f"🔍 查询: {section}")

            info = self.get_section_details(section, skip_refresh=True)

            if info:
                results[section] = info
                if callback:
                    msg = f"✓ {section}: 剩余 {info['available']} / 总共 {info['capacity']} (Waitlist: {info['waitlist']})"
                    callback(msg)

                # --- 自动抢课逻辑 ---
                if info['available'] > 0 and auto_register:
                    if callback:
                        callback(f"⚡ 发现空位! 正在尝试点击 Register Now...")

                    # 尝试点击注册
                    success = self.attempt_registration()

                    if success:
                        if callback:
                            callback(f"🚀 已触发注册点击! 请检查浏览器确认结果!")
                            # 点击后可能需要暂停监控以免干扰，或者继续？这里选择继续，但稍微等待
                            time.sleep(2)
                    else:
                        if callback: callback(f"❌ 自动点击失败，请手动注册!")

            else:
                if callback: callback(f"⚠️  无法获取 {section}")

            time.sleep(0.2)

        return results


class CourseMonitorGUI:
    def show_disclaimer(self) -> bool:
        """显示免责声明并要求用户确认"""
        title = "重要免责声明 (Important Disclaimer)"
        message = (
            "本软件仅供**学习交流使用**，请勿用于违反学校规定或不正当用途。\n\n"
            "⚠️ 作者不对因使用本软件导致的任何后果负责，包括但不限于：\n"
            "   1. 选课失败或操作失误。\n"
            "   2. 学校系统（如 Ellucian Colleague）账号被封禁或遭受处罚。\n"
            "   3. 浏览器更新导致的程序失效。\n\n"
            "您必须**同意**上述条款才能继续使用本程序。"
        )

        # 使用 askokcancel 强制用户选择“确定”
        if messagebox.askokcancel(title, message, icon='warning'):
            return True
        else:
            return False

    def __init__(self):
        self.monitor = None
        self.monitoring = False
        self.monitor_thread = None
        self.root = tk.Tk()
        # >>> 新增: 在设置UI前显示免责声明
        if not self.show_disclaimer():
            self.root.destroy()
            return
        # <<<

        # === 新增：设置窗口图标 ===
        try:
            self.root.iconbitmap(resource_path('icon.ico'))
        except Exception as e:
            print(f"加载图标失败: {e}")

        self.root.title("Kean University 课程监控系统")
        self.root.geometry("900x750")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.setup_ui()

    def setup_ui(self):
        """构建UI"""
        # --- 登录框架 ---
        login_frame = ttk.LabelFrame(self.root, text="🔐 浏览器设置", padding=10)
        login_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(login_frame, text="浏览器:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.browser_var = tk.StringVar(value="edge")
        browser_frame = ttk.Frame(login_frame)
        browser_frame.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        ttk.Radiobutton(browser_frame, text="Edge (推荐)", variable=self.browser_var, value="edge").pack(side='left',
                                                                                                         padx=5)
        ttk.Radiobutton(browser_frame, text="Chrome", variable=self.browser_var, value="chrome").pack(side='left',
                                                                                                      padx=5)

        self.login_btn = ttk.Button(login_frame, text="🌐 打开浏览器并登录", command=self.open_browser, width=25)
        self.login_btn.grid(row=0, column=2, padx=10)

        self.manual_confirm_btn = ttk.Button(login_frame, text="✅ 手动确认已登录", command=self.manual_confirm_login,
                                             width=20, state='disabled')
        self.manual_confirm_btn.grid(row=0, column=3, padx=5)

        ttk.Label(login_frame, text="💡 提示: 点击后请在浏览器中手动登录Kean账号", font=('', 9), foreground='blue').grid(
            row=1, column=0, columnspan=4, sticky='w', padx=5, pady=5)

        # --- 监控设置 ---
        monitor_frame = ttk.LabelFrame(self.root, text="📚 监控设置", padding=10)
        monitor_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(monitor_frame, text="学期:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.term_entry = ttk.Entry(monitor_frame, width=50)
        self.term_entry.grid(row=0, column=1, padx=5, pady=5)
        self.term_entry.insert(0, "Winter 2026 Wenzhou")

        ttk.Label(monitor_frame, text="Section代码:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.sections_entry = ttk.Entry(monitor_frame, width=50)
        self.sections_entry.grid(row=1, column=1, padx=5, pady=5)
        self.sections_entry.insert(0, "COMM*1402*W01")

        ttk.Label(monitor_frame, text="检查间隔(秒):").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.interval_entry = ttk.Entry(monitor_frame, width=10)
        self.interval_entry.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        self.interval_entry.insert(0, "60")

        # --- 新增: 自动抢课开关 ---
        self.auto_register_var = tk.BooleanVar(value=False)
        self.auto_register_cb = ttk.Checkbutton(monitor_frame, text="⚡ 发现空位自动点击 'Register Now' (风险自负)",
                                                variable=self.auto_register_var, onvalue=True, offvalue=False)
        self.auto_register_cb.grid(row=3, column=1, sticky='w', padx=5, pady=5)

        # --- 控制按钮 ---
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill='x', padx=10, pady=5)

        self.test_btn = ttk.Button(btn_frame, text="🧪 测试一次", command=self.test_once, state='disabled')
        self.test_btn.pack(side='left', padx=5)

        self.start_btn = ttk.Button(btn_frame, text="▶️ 开始监控", command=self.start_monitoring, state='disabled')
        self.start_btn.pack(side='left', padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="⏹️ 停止监控", command=self.stop_monitoring, state='disabled')
        self.stop_btn.pack(side='left', padx=5)

        # ... (在控制按钮 btn_frame 之后) ...

        # --- 重要的免责声明标签 ---
        disclaimer_text = "⚠️ 本软件仅供学习交流使用，作者不对因使用本软件导致的任何后果（如选课失败、账号被封等）负责。"
        disclaimer_label = ttk.Label(self.root, text=disclaimer_text,
                                     font=('Arial', 10, 'bold'),
                                     foreground='red',
                                     anchor='center')
        disclaimer_label.pack(fill='x', padx=10, pady=5)

        # --- NEW: 广告/推广区域 (增强版) ---
        ad_frame = ttk.LabelFrame(self.root, text="📢 社区推广与建议", padding=5)
        ad_frame.pack(fill='x', padx=10, pady=5)

        # 推广链接
        ad_text_main = "温州肯恩大学吧"
        ad_url = "https://tieba.baidu.com/f?ie=utf-8&kw=%E6%B8%A9%E5%B7%9E%E8%82%AF%E6%81%A9%E5%A4%A7%E5%AD%A6"

        # 1. 核心推广语（可点击链接）
        link_frame = ttk.Frame(ad_frame)
        link_frame.pack(fill='x', padx=5, pady=2)

        ttk.Label(link_frame, text="✅ 社区推荐：", font=('Arial', 10, 'bold')).pack(side='left')
        link_label = ttk.Label(link_frame, text=ad_text_main,
                               font=('Arial', 10, 'underline', 'bold'),
                               foreground='blue',
                               cursor='hand2')
        link_label.pack(side='left')
        link_label.bind("<Button-1>", lambda e: webbrowser.open(ad_url))

        # 2. 对“万能墙”的建议
        ttk.Label(ad_frame,
                  text="📢 号召：希望同学们减少使用'万能墙'，其使用体验极差且被留学机构掌控下商业推广现象极为猖獗。",
                  font=('Arial', 9),
                  foreground='darkred').pack(fill='x', padx=5, pady=2)

        ttk.Label(ad_frame,
                  text="💡 推荐大家使用并积极维护：温州肯恩大学吧。",
                  font=('Arial', 9, 'bold'),
                  foreground='green').pack(fill='x', padx=5, pady=2)

        # --- 日志 ---
        log_frame = ttk.LabelFrame(self.root, text="📋 日志", padding=5)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state='disabled', font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True)

        # --- 底部作者/版权信息区域 ---
        footer_frame = ttk.Frame(self.root, padding="10 2 10 2")
        footer_frame.pack(fill='x', side='bottom')

        # 1. 开发者姓名
        ttk.Label(footer_frame, text="Developed by Limitime", font=('Arial', 9, 'bold')).pack(side='left', padx=5)

        # 2. B站链接 (可点击)
        bili_url = "https://space.bilibili.com/477852567"
        bili_label = ttk.Label(footer_frame, text="Bilibili主页",
                               font=('Arial', 9, 'underline', 'bold'), foreground='blue', cursor='hand2')
        bili_label.pack(side='left', padx=5)
        bili_label.bind("<Button-1>", lambda e: webbrowser.open(bili_url))

        # 3. 静态微信号
        ttk.Label(footer_frame, text=" | 微信: Limitime107",
                  font=('Arial', 9, 'bold'), foreground='green').pack(side='left', padx=5)

        # 4. 静态QQ号
        ttk.Label(footer_frame, text=" | QQ: [869920298]",
                  font=('Arial', 9, 'bold'), foreground='red').pack(side='left', padx=5)

        # 5. 邮箱 (可点击)
        my_email = "Daozhu1007@outlook.com"
        email_label = ttk.Label(footer_frame, text=f" | Email: {my_email}",
                                font=('Arial', 9, 'bold'), foreground='purple', cursor='hand2')
        email_label.pack(side='left', padx=5)
        email_label.bind("<Button-1>", lambda e: webbrowser.open(f"mailto:{my_email}"))

        # --- 版本信息 (在右侧) ---
        VERSION = "1.0.0"  # 确保您的代码顶部也定义了 VERSION
        version_label = ttk.Label(footer_frame, text=f"v{VERSION}", font=('Arial', 9), foreground='gray')
        version_label.pack(side='right', padx=10)

        # 确保 VERSION 变量在代码顶部定义，例如:
        # VERSION = "1.0.0"

        # 状态栏
        self.status_label = ttk.Label(self.root, text="未登录", relief='sunken', anchor='w')
        self.status_label.pack(fill='x', side='bottom')

        # 欢迎
        self.log("=" * 70)
        self.log("🎓 Kean University 课程监控系统 - 专业版")
        self.log("=" * 70)
        # --- NEW: 作者声明 ---
        self.log("📢📢 作者声明 (Designer's Note) 📢📢")
        self.log("黄牛占课现象猖獗，严重侵害了同学们的公平选课权益。")
        self.log("希望凭借我的微薄力量和本软件的效率，能有效改善目前的现状。")
        self.log("欢迎大家共同维护校园社区的公平和秩序！")
        self.log("-" * 70)
        # --- 结束作者声明 ---
        self.log("✅ 极速内核: 优化了翻页和抓取速度")
        self.log("✅ 自动抢课: 发现空位可尝试自动点击注册")
        self.log("⚠️ 注意: 自动抢课功能请谨慎使用，建议先手动测试")
        if HAS_WEBDRIVER_MANAGER:
            self.log("✅ webdriver-manager已安装")
        else:
            self.log("⚠️  建议: pip install webdriver-manager")
        self.log("")

    def log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.config(state='normal')
        self.log_text.insert('end', f"[{timestamp}] {message}\n")
        self.log_text.see('end')
        self.log_text.config(state='disabled')

    def open_browser(self):
        """打开浏览器等待用户登录"""
        browser = self.browser_var.get()
        self.log(f"🚀 启动 {browser.upper()} 浏览器...")
        self.log("⏳ 请在浏览器中手动登录...")
        self.login_btn.config(state='disabled')
        self.manual_confirm_btn.config(state='normal')

        def login_thread():
            try:
                self.monitor = KeanCourseMonitor(browser=browser, headless=False)
                success, message = self.monitor.open_browser_and_wait_login()
                self.root.after(0, lambda: self.login_complete(success, message))
            except Exception as e:
                self.root.after(0, lambda: self.login_complete(False, str(e)))

        threading.Thread(target=login_thread, daemon=True).start()

    def manual_confirm_login(self):
        """手动确认已登录"""
        if not self.monitor or not self.monitor.driver:
            messagebox.showwarning("警告", "请先打开浏览器")
            return

        self.log("🔍 手动检查登录状态...")
        try:
            current_url = self.monitor.driver.current_url
            page_source = self.monitor.driver.page_source

            if 'DegreePlans' in current_url or 'Planning' in current_url:
                self.monitor.is_authenticated = True
                self.login_complete(True, "手动确认登录成功")
            elif 'Plan your Degree' in page_source or 'Schedule your courses' in page_source:
                self.monitor.is_authenticated = True
                self.login_complete(True, "手动确认登录成功")
            else:
                self.log(f"⚠️  当前URL: {current_url}")
                messagebox.showwarning("提示", f"请确保已经登录到选课页面!\n\n当前页面: {current_url[:100]}")
        except Exception as e:
            messagebox.showerror("错误", f"检查登录状态失败: {str(e)}")

    def login_complete(self, success: bool, message: str):
        """登录完成"""
        self.login_btn.config(state='normal')
        self.manual_confirm_btn.config(state='disabled')

        if success:
            self.log(f"✅ {message}")
            self.status_label.config(text=f"✅ 已登录 - 浏览器保持打开")
            self.test_btn.config(state='normal')
            self.start_btn.config(state='normal')
            messagebox.showinfo("登录成功", "已成功登录!\n\n请不要关闭浏览器窗口!")
        else:
            self.log(f"❌ {message}")
            if self.monitor:
                self.monitor.driver = None
            messagebox.showerror("登录失败", message)

    def test_once(self):
        """测试一次"""
        self.log("\n" + "=" * 70)
        self.log("🧪 开始测试...")
        self.test_btn.config(state='disabled')

        def test_thread():
            try:
                term = self.term_entry.get().strip()
                sections_input = self.sections_entry.get().strip()
                sections = [s.strip().upper() for s in sections_input.split(',')]
                auto_reg = self.auto_register_var.get()

                self.root.after(0, lambda: self.log(f"📅 目标学期: {term}"))
                self.root.after(0, lambda: self.log(f"📚 Sections: {', '.join(sections)}"))
                self.root.after(0, lambda: self.log(f"⚡ 自动抢课: {'开启' if auto_reg else '关闭'}"))

                results = self.monitor.monitor_sections(
                    term, sections, auto_register=auto_reg,
                    callback=lambda msg: self.root.after(0, lambda m=msg: self.log(m))
                )

                if results:
                    self.root.after(0, lambda: self.log("\n✅ 测试完成!"))
                else:
                    self.root.after(0, lambda: self.log("\n⚠️  未获取到数据"))

                self.root.after(0, lambda: self.test_btn.config(state='normal'))

            except Exception as e:
                msg = f"❌ 测试错误: {str(e)}"
                self.root.after(0, lambda m=msg: self.log(m))
                self.root.after(0, lambda: self.test_btn.config(state='normal'))

        threading.Thread(target=test_thread, daemon=True).start()

    def start_monitoring(self):
        """开始持续监控"""
        term = self.term_entry.get().strip()
        sections_input = self.sections_entry.get().strip()

        if not term or not sections_input:
            messagebox.showwarning("警告", "请输入学期和Section代码")
            return

        sections = [s.strip().upper() for s in sections_input.split(',')]
        interval = int(self.interval_entry.get() or 60)
        auto_reg = self.auto_register_var.get()

        self.monitoring = True
        self.start_btn.config(state='disabled')
        self.test_btn.config(state='disabled')
        self.stop_btn.config(state='normal')

        # 禁用设置以防运行中修改
        self.auto_register_cb.config(state='disabled')

        self.log("\n" + "=" * 70)
        self.log(f"🔍 开始持续监控")
        self.log(f"📅 学期: {term}")
        self.log(f"📚 Sections: {', '.join(sections)}")
        self.log(f"⚡ 自动抢课: {'开启' if auto_reg else '关闭'}")
        self.log(f"⏱️  间隔: {interval}秒")
        self.log("=" * 70 + "\n")

        def monitor_loop():
            previous_data = {}
            check_count = 0

            while self.monitoring:
                try:
                    check_count += 1
                    self.root.after(0, lambda c=check_count: self.log(f"\n━━━ 第 {c} 次检查 ━━━"))

                    # 获取最新的auto_register状态 (虽然UI禁用了，但逻辑上保持读取变量)
                    current_auto_reg = self.auto_register_var.get()

                    results = self.monitor.monitor_sections(
                        term, sections, auto_register=current_auto_reg,
                        callback=lambda msg: self.root.after(0, lambda m=msg: self.log(m))
                    )

                    # 检查变化
                    for section, info in results.items():
                        curr_available = info['available']
                        if section in previous_data:
                            prev_available = previous_data[section]['available']
                            if curr_available > prev_available:
                                msg = f"🎉🎉🎉 【{section}】有新座位! {prev_available} → {curr_available}"
                                self.root.after(0, lambda m=msg: self.log(m))
                                self.root.after(0, lambda: self.root.bell())
                            elif curr_available < prev_available:
                                msg = f"⚠️  【{section}】座位减少 {prev_available} → {curr_available}"
                                self.root.after(0, lambda m=msg: self.log(m))
                            else:
                                msg = f"📊 【{section}】座位未变化: {curr_available}"
                                self.root.after(0, lambda m=msg: self.log(m))
                        previous_data[section] = info

                    next_time = datetime.fromtimestamp(datetime.now().timestamp() + interval)
                    msg = f"⏱️  下次检查时间: {next_time.strftime('%H:%M:%S')}"
                    self.root.after(0, lambda m=msg: self.log(m))
                    time.sleep(interval)

                except Exception as e:
                    msg = f"❌ 监控错误: {str(e)}"
                    self.root.after(0, lambda m=msg: self.log(m))
                    time.sleep(interval)

            self.root.after(0, lambda: self.log("\n⏹️  监控已停止\n"))

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        self.start_btn.config(state='normal')
        self.test_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.auto_register_cb.config(state='normal')

    def on_closing(self):
        """关闭窗口"""
        if self.monitoring:
            if not messagebox.askokcancel("确认", "监控正在进行中,确定要关闭吗?"): return
        self.monitoring = False
        self.root.destroy()
        if self.monitor: self.monitor.driver = None

    def run(self):
        """运行应用"""
        self.root.mainloop()


if __name__ == "__main__":
    app = CourseMonitorGUI()
    app.run()
