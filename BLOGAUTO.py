import gradio as gr
import time
import threading
import random
import math
import json
import os
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime

# --- 자동화 로직을 담당하는 클래스 ---
class NaverBlogBot:
    """
    Selenium을 사용하여 네이버 블로그 자동화 작업을 수행하는 핵심 로직 클래스.
    UI와 독립적으로 동작합니다.
    """
    def __init__(self):
        self.driver = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()  # 시작 시에는 PAUSE 상태가 아님 (set() -> True)

    def _initialize_driver(self):
        """
        안정성을 강화한 WebDriver 초기화 메서드.
        Selenium 4의 내장 드라이버 관리자(Selenium Manager)를 사용합니다.
        """
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--start-maximized")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-gpu")
            options.add_argument("--log-level=3")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            
            # Service() 객체를 인자 없이 생성하여 Selenium Manager를 사용하도록 합니다.
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.implicitly_wait(5)
            return True
        except Exception as e:
            # 오류 발생 시 더 상세한 정보를 제공
            error_message = f"드라이버 초기화 실패: {repr(e)}\n"
            error_message += "1. Chrome 브라우저가 설치되어 있는지 확인해주세요.\n"
            error_message += "2. 인터넷 연결을 확인해주세요.\n"
            error_message += "3. 백신 프로그램이 chromedriver 실행을 차단하는지 확인해주세요."
            self.log_callback(error_message, "ERROR")
            return False

    def set_log_callback(self, callback):
        """UI에 로그를 전달하기 위한 콜백 함수를 설정합니다."""
        self.log_callback = callback

    def stop(self):
        self.stop_event.set()

    def pause(self):
        self.pause_event.clear()

    def resume(self):
        self.pause_event.set()

    def _wait_for_manual_login(self):
        """사용자가 수동으로 로그인할 때까지 대기하고, 그 전에 IP 보안을 해제합니다."""
        self.driver.get('https://nid.naver.com/nidlogin.login')
        self.log_callback("로그인 페이지로 이동했습니다.")
        
        # IP 보안 해제
        try:
            ip_security_switch = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.switch_on"))
            )
            ip_security_switch.click()
            self.log_callback("IP 보안 기능을 OFF로 설정했습니다.")
        except TimeoutException:
            self.log_callback("IP 보안이 이미 OFF 상태이거나 버튼을 찾을 수 없습니다.", "WARN")
        except Exception as e:
            self.log_callback(f"IP 보안 설정 중 오류 발생: {e}", "ERROR")

        self.log_callback("브라우저에서 직접 로그인해주세요. 로그인 완료 후 자동으로 시작됩니다.")
        
        try:
            # 사용자가 로그인하여 네이버 메인 페이지로 이동할 때까지 최대 10분 대기
            WebDriverWait(self.driver, 600).until(
                EC.url_contains("www.naver.com")
            )
            self.log_callback("로그인 성공을 감지했습니다! 자동화를 시작합니다.")
            return True
        except TimeoutException:
            self.log_callback("로그인 시간(10분)이 초과되었습니다. 봇을 종료합니다.", "ERROR")
            return False

    def _human_like_scroll(self):
        """인간적인 스크롤 애니메이션 로직"""
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        num_scrolls = random.randint(5, 7)
        scroll_percentages = [random.uniform(0.15, 0.25) for _ in range(num_scrolls)]
        total_ratio = sum(scroll_percentages)
        scroll_percentages = [p / total_ratio for p in scroll_percentages]
        current_scroll_position = self.driver.execute_script("return window.pageYOffset;")

        for percent in scroll_percentages:
            if self.stop_event.is_set(): break
            self.pause_event.wait()
            scroll_distance = total_height * percent
            start_pos = current_scroll_position
            animation_steps = random.randint(40, 60)
            total_duration = random.uniform(0.51, 0.72)

            for i in range(1, animation_steps + 1):
                if self.stop_event.is_set(): break
                self.pause_event.wait()
                t = i / animation_steps
                progress = -(math.cos(math.pi * t) - 1) / 2
                scroll_to = start_pos + (scroll_distance * progress)
                self.driver.execute_script(f"window.scrollTo(0, {scroll_to});")
                time.sleep(total_duration / animation_steps)
            
            current_scroll_position = start_pos + scroll_distance
            self.driver.execute_script(f"window.scrollTo(0, {current_scroll_position});")

            if random.random() < 0.25:
                correction = (random.random() - 0.5) * 0.05 * total_height
                self.driver.execute_script(f"window.scrollBy(0, {correction});")
                time.sleep(random.uniform(0.2, 0.4))
                current_scroll_position += correction

            if random.random() < 0.4:
                time.sleep(random.uniform(0.3, 0.6))
        
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        self.log_callback("  └ 페이지를 자연스럽게 스크롤했습니다.")

    def _like_posts(self):
        """공감 작업 메인 로직"""
        current_page = 1
        total_liked_count = 0
        self.log_callback("이웃 새글 공감 작업을 시작합니다.")

        while True:
            self.pause_event.wait()
            if self.stop_event.is_set(): break
            
            target_url = f"https://section.blog.naver.com/BlogHome.naver?directoryNo=0&currentPage={current_page}&groupId=0"
            self.driver.get(target_url)
            self.log_callback(f"이웃 새글 {current_page}페이지로 이동했습니다.")
            time.sleep(2.5)

            if not self.driver.find_elements(By.CSS_SELECTOR, "div.list_post_article"):
                self.log_callback("현재 페이지에서 더 이상 글을 찾지 못했습니다. 작업을 종료합니다.", "INFO")
                break
            
            while True:
                self.pause_event.wait()
                if self.stop_event.is_set(): break

                post_containers = self.driver.find_elements(By.CSS_SELECTOR, "div.list_post_article")
                if not post_containers: break
                
                post = post_containers[0]
                post_title = "제목을 찾을 수 없음"
                
                try:
                    post_title = post.find_element(By.CSS_SELECTOR, "span[ng-bind='post.title']").text
                    like_button_in_list = post.find_element(By.CSS_SELECTOR, "a.u_likeit_list_btn._button")
                    delete_button = post.find_element(By.CSS_SELECTOR, "i.icon_delete")

                    if like_button_in_list.get_attribute("aria-pressed") == 'true':
                        self.log_callback(f"└ '{post_title}' 글은 이미 공감 상태입니다. 목록에서 삭제합니다.", "INFO")
                        self.driver.execute_script("arguments[0].click();", delete_button)
                        time.sleep(1.5)
                        continue

                    post_link = post.find_element(By.CSS_SELECTOR, "a.text[ng-href]")
                    self.driver.get(post_link.get_attribute("href"))
                    self.log_callback(f"└ '{post_title}' 포스트로 이동합니다.")
                    
                    WebDriverWait(self.driver, 10).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "mainFrame")))
                    self._human_like_scroll()

                    like_button_in_post = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[class*='u_likeit_list_btn'][aria-pressed='false']"))
                    )
                    self.driver.execute_script("arguments[0].click();", like_button_in_post)
                    total_liked_count += 1
                    self.log_callback(f"  └ 공감했습니다! (총 {total_liked_count}개)", "SUCCESS")
                    time.sleep(1.5)

                except TimeoutException:
                    self.log_callback(f"  └ '{post_title}'은(는) 이미 공감했거나 버튼을 찾을 수 없어 건너뜁니다.", "WARN")
                except NoSuchElementException:
                    self.log_callback(f"└ '{post_title}'은(는) 비표준 포스트(광고 등)로 추정되어 건너뛰고 삭제합니다.", "WARN")
                    try:
                        delete_button = post.find_element(By.CSS_SELECTOR, "i.icon_delete")
                        self.driver.execute_script("arguments[0].click();", delete_button)
                        time.sleep(1.5)
                    except NoSuchElementException:
                        self.driver.refresh()
                        time.sleep(2)
                    continue
                except Exception as e:
                    self.log_callback(f"  └ '{post_title}' 처리 중 예외 발생: {repr(e)}", "ERROR")
                finally:
                    self.driver.switch_to.default_content()
                    self.driver.get(target_url)
                    WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.list_post_article")))
                    
                    try:
                        first_post = self.driver.find_element(By.CSS_SELECTOR, "div.list_post_article")
                        delete_button = first_post.find_element(By.CSS_SELECTOR, "i.icon_delete")
                        self.driver.execute_script("arguments[0].click();", delete_button)
                        self.log_callback("  └ 목록에서 완료된 글을 삭제했습니다.")
                        time.sleep(1.5)
                    except Exception: pass

            if self.stop_event.is_set(): break
            current_page += 1
        
        if not self.stop_event.is_set():
            self.log_callback(f"작업 완료! 총 {total_liked_count}개의 포스트에 공감했습니다.", "SUCCESS")

    def run(self):
        """자동화 봇의 전체 실행 로직"""
        self.stop_event.clear()
        self.pause_event.set()
        
        if not self._initialize_driver():
            self.log_callback("봇을 시작할 수 없습니다. 프로그램을 종료합니다.", "ERROR")
            return

        if self._wait_for_manual_login():
            self._like_posts()
        
        if self.driver:
            self.driver.quit()
        
        if self.stop_event.is_set():
            self.log_callback("사용자에 의해 작업이 중단되었습니다.", "WARN")
        else:
            self.log_callback("모든 작업이 완료되어 봇을 종료합니다.", "INFO")

# --- Gradio UI를 관리하는 클래스 ---
class GradioApp:
    def __init__(self):
        self.bot = NaverBlogBot()
        self.bot_thread = None
        self.log_content = ""

    def _log_updater(self, message, log_type="INFO"):
        """NaverBlogBot에서 로그를 받아 UI에 업데이트합니다."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_content += f"[{timestamp}][{log_type}] {message}\n"

    def start_bot(self):
        self.log_content = "" # 로그 초기화
        self.bot = NaverBlogBot()
        self.bot.set_log_callback(self._log_updater)
        
        self.bot_thread = threading.Thread(target=self.bot.run, daemon=True)
        self.bot_thread.start()

        # UI 업데이트를 위한 제너레이터 시작
        yield self.log_content, "RUNNING", gr.update(visible=True, value="⏸️ 일시정지"), gr.update(visible=True)

        while self.bot_thread.is_alive():
            yield self.log_content, "RUNNING", gr.update(), gr.update()
            time.sleep(1)
        
        yield self.log_content, "FINISHED", gr.update(visible=False), gr.update(visible=False)

    def stop_bot(self):
        if self.bot:
            self.bot.stop()
        return "STOPPED", gr.update(visible=False), gr.update(visible=False)

    def toggle_pause_resume(self, current_state):
        if current_state == "RUNNING":
            self.bot.pause()
            return "PAUSED", gr.update(value="▶️ 재개")
        elif current_state == "PAUSED":
            self.bot.resume()
            return "RUNNING", gr.update(value="⏸️ 일시정지")
        return current_state, gr.update()

    def shutdown_server(self):
        def _shutdown():
            time.sleep(1)
            # Gradio 앱을 정상적으로 닫고 프로세스를 종료합니다.
            self.app.close()
            os._exit(0)
        threading.Thread(target=_shutdown, daemon=True).start()
        return "서버를 1초 후에 종료합니다..."

    def launch(self):
        with gr.Blocks(theme=gr.themes.Base(primary_hue=gr.themes.colors.green, secondary_hue=gr.themes.colors.blue), title="Naver Blog Auto-Liker") as app:
            bot_state = gr.State("IDLE")

            with gr.Row():
                gr.HTML("""
                    <div style="display: flex; align-items: center; justify-content: center; gap: 12px;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-heart-handshake"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/><path d="M12 5 9.04 7.96a2.17 2.17 0 0 0 0 3.08v0c.82.82 2.13.82 2.94 0l.06-.06L12 11l2.96-2.96c.82-.82 2.13.82 2.94 0l0 0a2.17 2.17 0 0 0 0-3.08L12 5Z"/></svg>
                        <h1 style="font-size: 2em; font-weight: 700;">Naver Blog Auto-Liker</h1>
                    </div>
                """)

            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("## ⚙️ 제어판 (Control Panel)")
                    with gr.Group():
                        gr.Markdown("### 봇 제어")
                        start_button = gr.Button("🤖 봇 시작", variant="primary")
                        with gr.Row():
                            pause_resume_button = gr.Button("⏸️ 일시정지", visible=False)
                            stop_button = gr.Button("🛑 봇 중지", visible=False)
                        shutdown_button = gr.Button("🔌 서버 종료", variant="stop")
                    gr.Markdown("### 📊 현재 상태 (Bot Status)")
                    status_output = gr.Textbox(value="IDLE", label="상태", interactive=False)
                with gr.Column(scale=2):
                    gr.Markdown("## 📝 상태 로그 (Status Log)")
                    log_output = gr.Textbox(label="실시간 로그", lines=25, interactive=False, autoscroll=True)

            # --- 이벤트 핸들러 연결 ---
            start_event = start_button.click(
                fn=self.start_bot,
                inputs=None,
                outputs=[log_output, bot_state, pause_resume_button, stop_button]
            )
            stop_button.click(
                fn=self.stop_bot,
                inputs=None,
                outputs=[bot_state, pause_resume_button, stop_button],
                cancels=[start_event]
            )
            pause_resume_button.click(
                fn=self.toggle_pause_resume,
                inputs=[bot_state],
                outputs=[bot_state, pause_resume_button]
            )
            shutdown_button.click(
                fn=self.shutdown_server,
                inputs=None,
                outputs=[status_output] # 메시지를 상태창에 표시
            )
        
        # app 객체를 클래스 변수로 저장하여 shutdown_server에서 접근 가능하도록 함
        self.app = app
        app.launch(inbrowser=True)

if __name__ == "__main__":
    ui = GradioApp()
    ui.launch()
