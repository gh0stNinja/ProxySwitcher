# -*- coding: utf-8 -*-
from burp import IBurpExtender, IHttpListener, ITab
from javax.swing import (
    JPanel, JLabel, JTextField, JButton, JCheckBox, JTextArea, JScrollPane,
    JComboBox, JPopupMenu, JMenuItem, JFileChooser, SwingUtilities,
    BoxLayout, Box
)
from javax.swing.border import EmptyBorder
from java.awt import BorderLayout, Font
from java.awt.event import MouseAdapter
from java.net import URL, Proxy, InetSocketAddress
from java.util.concurrent import Executors, CountDownLatch, TimeUnit
from java.lang import System
from java.awt.datatransfer import StringSelection
from java.awt.Toolkit import getDefaultToolkit
import random
import json
import re
import threading
from functools import partial

# --------------------------------------------------------------
#  BurpExtender - Proxy Switcher v2.0 (No Smart Mode)
#  UI：IP:PORT | TYPE | HTTP/HTTPS | 延迟ms | OK/FAIL
# --------------------------------------------------------------
class BurpExtender(IBurpExtender, IHttpListener, ITab):
    def registerExtenderCallbacks(self, callbacks):
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        self._callbacks.setExtensionName("Proxy Switcher v2.0")
        self._callbacks.registerHttpListener(self)

        # ---------- 语言系统（所有字符串加 u 前缀） ----------
        self.lang = "zh"
        self.I18N = {
            "zh": {
                "Enable": u"启用",
                "Clear Log": u"清空日志",
                "Verify All": u"验证全部",
                "Import": u"导入",
                "Export": u"导出",
                "Clear List": u"清空列表",
                "Get": u"获取",
                "Url: ": u"地址：",
                "Proxy List (Right-click)": u"代理列表（右键操作）",
                "Log": u"日志",
                "Delete": u"删除代理",
                "Test Selected": u"验证选中",
                "Set Fix": u"固定代理",
                "Copy as cURL": u"复制为 cURL",
                "Remove Dead": u"移除无效",

                "Plugin Enabled": u"插件已启用",
                "Plugin Disabled": u"插件已停用",
                "Enter URL": u"请输入 URL",
                "Fetched %d proxies": u"已获取 %d 个代理",
                "Fetch failed: %s": u"获取失败：%s",
                "Imported %d": u"已导入 %d 个",
                "Import failed": u"导入失败",
                "No proxies to export": u"无代理可导出",
                "Export failed": u"导出失败",
                "List cleared": u"列表已清空",
                "Mode: %s": u"模式：%s",
                "No proxies": u"暂无代理",
                "Verification in progress...": u"验证进行中...",
                "Verifying %d proxies...": u"正在验证 %d 个代理...",
                "Done. Valid: %d/%d": u"完成，有效：%d/%d",
                "Verified: %d/%d": u"已验证：%d/%d",
                "No proxy selected": u"未选中任何代理",
                "Invalid selection": u"选择无效",
                "No valid proxies found": u"未找到有效代理",
                "Testing %d selected %s...": u"正在测试 %d 个选中%s...",
                "Tested: %d/%d": u"已测试：%d/%d",
                "Done: %d valid out of %d": u"完成：%d 有效，共 %d 个",
                "Test error: %s": u"测试出错：%s",
                "Fix: %s": u"固定代理：%s",
                "Removed %d dead proxies": u"已移除 %d 个无效代理",
                "[%s] Using: %s": u"[%s] 使用：%s",
                "proxy": u"代理",
                "proxies": u"代理",
                "Proxy Switcher v2.0 loaded": u"Proxy Switcher v2.0 已加载",
            },
            "en": {
                "Enable": u"Enable",
                "Clear Log": u"Clear Log",
                "Verify All": u"Verify All",
                "Import": u"Import",
                "Export": u"Export",
                "Clear List": u"Clear List",
                "Get": u"Get",
                "Url: ": u"Url: ",
                "Proxy List (Right-click)": u"Proxy List (Right-click)",
                "Log": u"Log",
                "Delete": u"Delete Proxy",
                "Test Selected": u"Test Selected",
                "Set Fix": u"Set Fix",
                "Copy as cURL": u"Copy as cURL",
                "Remove Dead": u"Remove Dead",

                "Plugin Enabled": u"Plugin Enabled",
                "Plugin Disabled": u"Plugin Disabled",
                "Enter URL": u"Enter URL",
                "Fetched %d proxies": u"Fetched %d proxies",
                "Fetch failed: %s": u"Fetch failed: %s",
                "Imported %d": u"Imported %d",
                "Import failed": u"Import failed",
                "No proxies to export": u"No proxies to export",
                "Export failed": u"Export failed",
                "List cleared": u"List cleared",
                "Mode: %s": u"Mode: %s",
                "No proxies": u"No proxies",
                "Verification in progress...": u"Verification in progress...",
                "Verifying %d proxies...": u"Verifying %d proxies...",
                "Done. Valid: %d/%d": u"Done. Valid: %d/%d",
                "Verified: %d/%d": u"Verified: %d/%d",
                "No proxy selected": u"No proxy selected",
                "Invalid selection": u"Invalid selection",
                "No valid proxies found": u"No valid proxies found",
                "Testing %d selected %s...": u"Testing %d selected %s...",
                "Tested: %d/%d": u"Tested: %d/%d",
                "Done: %d valid out of %d": u"Done: %d valid out of %d",
                "Test error: %s": u"Test error: %s",
                "Fix: %s": u"Fix: %s",
                "Removed %d dead proxies": u"Removed %d dead proxies",
                "[%s] Using: %s": u"[%s] Using: %s",
                "proxy": u"proxy",
                "proxies": u"proxies",
                "Proxy Switcher v2.0 loaded": u"Proxy Switcher v2.0 loaded",
            }
        }

        self.enabled        = False
        self.proxies        = []
        self.current_index  = 0
        self.proxy_mode     = "random"
        self.sticky_proxy   = None
        self.executor       = None

        self.total_count    = 0
        self.verified_count = 0
        self.latch          = None

        self.init_gui()
        self._callbacks.addSuiteTab(self)

        # === 初始化映射表 ===
        self.display_to_mode = {
            u"随机": "random", u"轮询": "round_robin", u"固定": "sticky",
            u"Random": "random", u"Round-Robin": "round_robin", u"Fix": "sticky"
        }
        self.mode_to_display = {v: k for k, v in self.display_to_mode.items()}

        self.update_mode_combo_options()
        self.mode_combo.addActionListener(self.on_mode_change)

        self.log(self._t("Proxy Switcher v2.0 loaded"))

    def getTabCaption(self):      return "Proxy Switcher"
    def getUiComponent(self):     return self.panel

    def _t(self, key, *args):
        txt = self.I18N[self.lang].get(key, key)
        if args:
            txt = txt % args
        return txt

    # ------------------- UI -------------------
    def init_gui(self):
        self.panel = JPanel(BorderLayout())
        top = JPanel()
        top.setLayout(BoxLayout(top, BoxLayout.X_AXIS))

        self.toggle         = JCheckBox(self._t("Enable"), actionPerformed=self.toggle_plugin)
        self.lang_combo     = JComboBox([u"中文", u"English"])
        self.lang_combo.setSelectedIndex(0)
        self.lang_combo.addActionListener(self.on_lang_change)

        self.clear_log_btn  = JButton(self._t("Clear Log"), actionPerformed=self.clear_log)
        self.verify_btn     = JButton(self._t("Verify All"), actionPerformed=self.start_verify)
        self.import_btn     = JButton(self._t("Import"), actionPerformed=self.import_proxies)
        self.export_btn     = JButton(self._t("Export"), actionPerformed=self.export_proxies)
        self.clear_list_btn = JButton(self._t("Clear List"), actionPerformed=self.clear_proxy_list)

        self.url_field      = JTextField("", 25)
        self.fetch_btn      = JButton(self._t("Get"), actionPerformed=self.fetch_proxies)

        self.mode_combo = JComboBox()

        # 布局
        top.add(self.toggle)
        top.add(Box.createHorizontalStrut(5))
        top.add(self.lang_combo)
        top.add(Box.createHorizontalStrut(10))
        top.add(JLabel(self._t("Url: ")))
        top.add(self.url_field)
        top.add(self.fetch_btn)
        top.add(Box.createHorizontalStrut(10))
        top.add(self.mode_combo)
        top.add(Box.createHorizontalStrut(10))
        top.add(self.verify_btn)
        top.add(self.import_btn)
        top.add(self.export_btn)
        top.add(self.clear_list_btn)
        top.add(self.clear_log_btn)

        # 中间面板
        mid = JPanel()
        mid.setLayout(BoxLayout(mid, BoxLayout.X_AXIS))

        # 代理列表
        left = JPanel(BorderLayout())
        left.add(JLabel(self._t("Proxy List (Right-click)")), BorderLayout.NORTH)
        self.proxy_area = JTextArea(18, 50)
        self.proxy_area.setEditable(False)
        self.proxy_area.setFont(Font("Monospaced", Font.PLAIN, 12))
        left.add(JScrollPane(self.proxy_area), BorderLayout.CENTER)

        # 右键菜单
        self.popup = JPopupMenu()
        self.popup.add(JMenuItem(self._t("Delete"),      actionPerformed=partial(self.remove_selected_proxy)))
        self.popup.add(JMenuItem(self._t("Set Fix"),   actionPerformed=partial(self.set_sticky_proxy)))
        self.popup.add(JMenuItem(self._t("Copy as cURL"), actionPerformed=partial(self.copy_as_curl)))
        self.popup.addSeparator()
        self.popup.add(JMenuItem(self._t("Verify All"),   actionPerformed=partial(self.start_verify)))
        self.popup.add(JMenuItem(self._t("Test Selected"),actionPerformed=partial(self.test_selected_proxies)))
        self.popup.addSeparator()
        self.popup.add(JMenuItem(self._t("Remove Dead"),  actionPerformed=partial(self.remove_dead)))

        self.proxy_area.addMouseListener(self.PopupTrigger(self.popup))

        # 日志面板
        right = JPanel(BorderLayout())
        right.add(JLabel(self._t("Log")), BorderLayout.NORTH)
        self.log_area = JTextArea(18, 35)
        self.log_area.setEditable(False)
        self.log_area.setFont(Font("Monospaced", Font.PLAIN, 11))
        right.add(JScrollPane(self.log_area), BorderLayout.CENTER)

        sep = JPanel()
        sep.setBorder(EmptyBorder(0, 5, 0, 5))
        mid.add(left)
        mid.add(sep)
        mid.add(right)
        self.panel.add(top, BorderLayout.NORTH)
        self.panel.add(mid, BorderLayout.CENTER)

    class PopupTrigger(MouseAdapter):
        def __init__(self, popup): self.popup = popup
        def mousePressed(self, e):
            if e.isPopupTrigger(): self.popup.show(e.getComponent(), e.getX(), e.getY())
        def mouseReleased(self, e):
            if e.isPopupTrigger(): self.popup.show(e.getComponent(), e.getX(), e.getY())

    # ------------------- 语言 & 模式 -------------------
    def on_lang_change(self, event):
        idx = self.lang_combo.getSelectedIndex()
        self.lang = "zh" if idx == 0 else "en"
        self.refresh_ui_texts()

    def update_mode_combo_options(self):
        current_mode = self.proxy_mode
        listeners = self.mode_combo.getActionListeners()
        for l in listeners: self.mode_combo.removeActionListener(l)
        self.mode_combo.removeAllItems()
        options = [u"随机", u"轮询", u"固定"] if self.lang == "zh" else [u"Random", u"Round-Robin", u"Fix"]
        for opt in options: self.mode_combo.addItem(opt)
        display = self.mode_to_display.get(current_mode, options[0])
        self.mode_combo.setSelectedItem(display)
        for l in listeners: self.mode_combo.addActionListener(l)

    def refresh_ui_texts(self):
        def _():
            self.toggle.setText(self._t("Enable"))
            self.clear_log_btn.setText(self._t("Clear Log"))
            self.verify_btn.setText(self._t("Verify All"))
            self.import_btn.setText(self._t("Import"))
            self.export_btn.setText(self._t("Export"))
            self.clear_list_btn.setText(self._t("Clear List"))
            self.fetch_btn.setText(self._t("Get"))

            if hasattr(self, 'popup'):
                items = self.popup.getComponents()
                texts = [
                    self._t("Delete"), self._t("Set Fix"), self._t("Copy as cURL"),
                    None,
                    self._t("Verify All"), self._t("Test Selected"),
                    None,
                    self._t("Remove Dead")
                ]
                for i, item in enumerate(items):
                    if i < len(texts) and texts[i] is not None:
                        item.setText(texts[i])

            self.update_mode_combo_options()
            self.panel.revalidate()
            self.panel.repaint()
        SwingUtilities.invokeLater(_)

    def log(self, text):
        def _():
            self.log_area.append(text + "\n")
            self.log_area.setCaretPosition(self.log_area.getDocument().getLength())
        SwingUtilities.invokeLater(_)

    def on_mode_change(self, event):
        sel = self.mode_combo.getSelectedItem()
        if sel:
            mode = self.display_to_mode.get(sel, "random")
            if mode != self.proxy_mode:
                self.proxy_mode = mode
                self.log(self._t("Mode: %s") % sel)

    # ------------------- 代理操作 -------------------
    def add_proxies(self, raw_list):
        existing = {x['proxy'] for x in self.proxies}
        for p in raw_list:
            p = p.strip()
            if p in existing:
                continue

            if p.lower().startswith(("socks5://", "socks://")):
                proxy_str = p.split("://", 1)[1]
                proxy_type = "socks5"
            elif re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', p):
                proxy_str = p
                proxy_type = "http"
            else:
                continue

            if proxy_str in existing:
                continue

            self.proxies.append({
                "proxy": proxy_str,
                "type": proxy_type,
                "http": False, "https": False,
                "delay": -1
            })
            existing.add(proxy_str)
        self.update_proxy_display()

    def update_proxy_display(self):
        def _():
            self.proxy_area.setText("")
            self.proxy_area.setFont(Font("Monospaced", Font.PLAIN, 12))
            for p in self.proxies:
                proto = "/".join([x for x in ["HTTP", "HTTPS"] if p.get(x.lower(), False)]) or "-"
                type_str = p['type'].upper()
                delay_str = "%dms" % p['delay'] if p['delay'] >= 0 else "N/A"
                status = "OK" if p['http'] or p['https'] else "FAIL"
                line = "%-20s | %-8s | %-6s | %-7s | %s" % (
                    (p['proxy'][:20]).ljust(20),
                    type_str.ljust(8),
                    proto.ljust(6),
                    delay_str.ljust(7),
                    status
                )
                self.proxy_area.append(line + "\n")
        SwingUtilities.invokeLater(_)

    # ------------------- 代理切换 -------------------
    def get_next_proxy(self):
        if not self.enabled or not self.proxies:
            return None

        valid = [p for p in self.proxies if p['http'] or p['https']]
        if not valid:
            return None

        if self.proxy_mode == "sticky" and self.sticky_proxy and self.sticky_proxy in [p['proxy'] for p in valid]:
            return self.sticky_proxy
        elif self.proxy_mode == "round_robin":
            proxy = valid[self.current_index % len(valid)]['proxy']
            self.current_index += 1
            return proxy
        else:  # random
            return random.choice(valid)['proxy']

    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        if not self.enabled or not messageIsRequest:
            return
        if toolFlag not in (self._callbacks.TOOL_INTRUDER, self._callbacks.TOOL_REPEATER):
            return
        proxy_str = self.get_next_proxy()
        if not proxy_str:
            return
        host, port = proxy_str.split(":")
        messageInfo.setHttpService(self._helpers.buildHttpService(host, int(port), "http"))
        tool = self._callbacks.getToolName(toolFlag)
        self.log(self._t("[%s] Using: %s") % (tool, proxy_str))

    # ------------------- 右键功能 -------------------
    def copy_as_curl(self, event=None):
        txt = self.proxy_area.getSelectedText()
        if not txt:
            self.log(self._t("No proxy selected"))
            return
        proxy = txt.split()[0]
        proxy_type = next((p['type'] for p in self.proxies if p['proxy'] == proxy), "http")
        scheme = "socks5" if proxy_type == "socks5" else "http"
        curl = 'curl -x %s://%s "http://httpbin.org/ip"' % (scheme, proxy)
        try:
            selection = StringSelection(curl)
            clipboard = getDefaultToolkit().getSystemClipboard()
            clipboard.setContents(selection, selection)
            self.log(u"Copied cURL: %s" % curl)
        except Exception as e:
            self.log(u"Clipboard error: %s" % str(e))

    # ------------------- 其余功能 -------------------
    def toggle_plugin(self, event):
        self.enabled = self.toggle.isSelected()
        self.log(self._t("Plugin Enabled") if self.enabled else self._t("Plugin Disabled"))

    def clear_log(self, event):
        self.log_area.setText("")

    def clear_proxy_list(self, event):
        self.proxies = []
        self.current_index = 0
        self.sticky_proxy = None
        self.update_proxy_display()
        self.log(self._t("List cleared"))

    def fetch_proxies(self, event):
        url = self.url_field.getText().strip()
        if not url:
            self.log(self._t("Enter URL"))
            return
        threading.Thread(target=partial(self._fetch, url)).start()

    def _fetch(self, url):
        try:
            conn = URL(url).openConnection()
            conn.setConnectTimeout(10000)
            conn.setReadTimeout(10000)
            data = self._helpers.bytesToString(conn.getInputStream().readAllBytes())
            proxies = self.parse_proxy_response(data)
            self.add_proxies(proxies)
            self.log(self._t("Fetched %d proxies") % len(proxies))
        except Exception as e:
            self.log(self._t("Fetch failed: %s") % str(e))

    def parse_proxy_response(self, data):
        proxies = set()
        try:
            if 'proxy' in data.lower() or 'ip' in data.lower():
                for p in json.loads(data):
                    ip = p.get('proxy') or p.get('ip') or \
                        (p.get('host') + ":" + str(p.get('port')) if p.get('host') else None)
                    if ip: proxies.add(ip.strip())
            else:
                for line in data.splitlines():
                    line = line.strip()
                    if re.match(r'^(socks5?://)?\d+\.\d+\.\d+\.\d+:\d+$', line, re.I):
                        proxies.add(line)
        except: pass
        return list(proxies)

    def import_proxies(self, event):
        chooser = JFileChooser()
        if chooser.showOpenDialog(self.panel) == JFileChooser.APPROVE_OPTION:
            path = chooser.getSelectedFile().getAbsolutePath()
            try:
                with open(path, 'r') as f:
                    lines = [l.strip() for l in f if l.strip()]
                self.add_proxies(lines)
                self.log(self._t("Imported %d") % len(lines))
            except Exception as e:
                self.log(self._t("Import failed"))

    def export_proxies(self, event):
        valid = [p for p in self.proxies if p['http'] or p['https']]
        if not valid:
            self.log(self._t("No proxies to export"))
            return
        chooser = JFileChooser()
        if chooser.showSaveDialog(self.panel) == JFileChooser.APPROVE_OPTION:
            path = chooser.getSelectedFile().getAbsolutePath()
            try:
                with open(path, 'w') as f:
                    f.write("\n".join([p['proxy'] for p in valid]))
                self.log(u"Exported valid proxies")
            except:
                self.log(self._t("Export failed"))

    def remove_selected_proxy(self, event=None):
        txt = self.proxy_area.getSelectedText()
        if txt:
            p = txt.split()[0]
            self.proxies = [x for x in self.proxies if x['proxy'] != p]
            self.update_proxy_display()

    def set_sticky_proxy(self, event=None):
        txt = self.proxy_area.getSelectedText()
        if txt:
            p = txt.split()[0]
            self.sticky_proxy = p
            self.log(self._t("Fix: %s") % p)

    def remove_dead(self, event=None):
        before = len(self.proxies)
        self.proxies = [p for p in self.proxies if p['http'] or p['https']]
        removed = before - len(self.proxies)
        self.update_proxy_display()
        self.log(self._t("Removed %d dead proxies") % removed)

    # ------------------- Verification -------------------
    def start_verify(self, event=None):
        if not self.proxies:
            self.log(self._t("No proxies"))
            return
        if hasattr(self, 'latch') and self.latch and self.latch.getCount() > 0:
            self.log(self._t("Verification in progress..."))
            return

        self.verify_btn.setEnabled(False)
        self.total_count = len(self.proxies)
        self.verified_count = 0
        self.latch = CountDownLatch(self.total_count)
        self.log(self._t("Verifying %d proxies...") % self.total_count)

        if not hasattr(self, 'executor') or not self.executor or self.executor.isShutdown():
            self.executor = Executors.newFixedThreadPool(30)

        for p in self.proxies:
            self.executor.submit(self.make_verifier(p))

        threading.Thread(target=self._wait_for_completion).start()

    def make_verifier(self, proxy_obj):
        def verifier():
            try:
                self.verify_single(proxy_obj)
            finally:
                self.latch.countDown()
        return verifier

    def _wait_for_completion(self):
        try:
            self.latch.await(300, TimeUnit.SECONDS)
            valid = len([p for p in self.proxies if p['http'] or p['https']])
            def final():
                self.log(self._t("Done. Valid: %d/%d") % (valid, self.total_count))
                self.update_proxy_display()
                self.verify_btn.setEnabled(True)
            SwingUtilities.invokeLater(final)
        except: pass

    def verify_single(self, proxy_obj):
        proxy = proxy_obj['proxy']
        host, port_str = proxy.split(":")
        port = int(port_str)

        http_delay  = self._test_protocol("http",  host, port, 2, proxy_obj['type'])
        https_delay = self._test_protocol("https", host, port, 2, proxy_obj['type'])

        proxy_obj['http']  = http_delay  >= 0
        proxy_obj['https'] = https_delay >= 0
        delays = [d for d in [http_delay, https_delay] if d >= 0]
        proxy_obj['delay'] = min(delays) if delays else -1

        self.verified_count += 1
        if self.verified_count % 10 == 0 or self.verified_count == self.total_count:
            SwingUtilities.invokeLater(lambda: self.log(
                self._t("Verified: %d/%d") % (self.verified_count, self.total_count)
            ))

    def _test_protocol(self, scheme, host, port, max_retry, proxy_type="http"):
        url_str = "%s://httpbin.org/ip" % scheme
        for attempt in range(max_retry):
            start = System.currentTimeMillis()
            try:
                ptype = Proxy.Type.SOCKS if proxy_type == "socks5" else Proxy.Type.HTTP
                proxy = Proxy(ptype, InetSocketAddress(host, port))
                conn = URL(url_str).openConnection(proxy)
                conn.setConnectTimeout(3000)
                conn.setReadTimeout(3000)
                conn.setRequestProperty("User-Agent", "Mozilla/5.0")
                code = conn.getResponseCode()
                elapsed = System.currentTimeMillis() - start
                if 200 <= code < 400:
                    return elapsed
                else:
                    return -1
            except:
                if attempt == max_retry - 1:
                    return -1
        return -1

    # ------------------- Test Selected -------------------
    def test_selected_proxies(self, event=None):
        selected_text = self.proxy_area.getSelectedText()
        if not selected_text:
            self.log(self._t("No proxy selected"))
            return

        lines = [line.strip() for line in selected_text.splitlines() if line.strip()]
        proxy_strs = []
        for line in lines:
            parts = line.split()
            if parts and re.match(r'^\d+\.\d+\.\d+\.\d+:\d+$', parts[0]):
                proxy_strs.append(parts[0])

        if not proxy_strs:
            self.log(self._t("Invalid selection"))
            return

        proxy_objs = [x for pstr in proxy_strs for x in self.proxies if x['proxy'] == pstr]
        if not proxy_objs:
            self.log(self._t("No valid proxies found"))
            return

        total = len(proxy_objs)
        unit = self._t("proxy") if total == 1 else self._t("proxies")
        self.log(self._t("Testing %d selected %s...") % (total, unit))

        if not hasattr(self, 'test_executor') or self.test_executor.isShutdown():
            self.test_executor = Executors.newFixedThreadPool(20)

        self.test_latch = CountDownLatch(total)
        self.test_count = 0
        self.test_total = total
        self.test_targets = proxy_objs

        for obj in proxy_objs:
            obj['http'] = obj['https'] = False
            obj['delay'] = -1
            self.test_executor.submit(self.make_test_verifier(obj))

        threading.Thread(target=self._wait_for_test_completion).start()

    def make_test_verifier(self, proxy_obj):
        def verifier():
            try:
                self.verify_single(proxy_obj)
            finally:
                self.test_latch.countDown()
                self.test_count += 1
                if self.test_count % 3 == 0 or self.test_count == self.test_total:
                    SwingUtilities.invokeLater(lambda: self.log(
                        self._t("Tested: %d/%d") % (self.test_count, self.test_total)
                    ))
        return verifier

    def _wait_for_test_completion(self):
        try:
            self.test_latch.await(180, TimeUnit.SECONDS)
            valid_count = sum(1 for p in self.test_targets if p['http'] or p['https'])
            total = len(self.test_targets)
            def final():
                self.log(self._t("Done: %d valid out of %d") % (valid_count, total))
                self.update_proxy_display()
            SwingUtilities.invokeLater(final)
        except Exception as e:
            SwingUtilities.invokeLater(lambda: self.log(self._t("Test error: %s") % str(e)))