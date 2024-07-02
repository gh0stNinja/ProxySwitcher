# -*- coding: utf-8 -*-
from burp import IBurpExtender, IHttpListener, ITab, IExtensionHelpers
from javax.swing import JPanel, JLabel, JTextField, JButton, JCheckBox, JTextArea, JScrollPane, JRadioButton, ButtonGroup, BoxLayout, Box
from javax.swing.border import EmptyBorder
from java.awt import BorderLayout
import java.net.URL
import random
import sys
import json

reload(sys)
sys.setdefaultencoding('utf8')

class BurpExtender(IBurpExtender, IHttpListener, ITab):
    def registerExtenderCallbacks(self, callbacks):
        # 初始化回调对象和辅助对象
        self._callbacks = callbacks
        self._helpers = callbacks.getHelpers()
        # 设置扩展名
        self._callbacks.setExtensionName("Proxy Switcher")
        # 注册HTTP监听器
        self._callbacks.registerHttpListener(self)
        
        # 创建GUI组件
        self.panel = JPanel()
        self.panel.setLayout(BorderLayout())
        
        self.top_panel = JPanel()
        self.toggle_plugin = JCheckBox(u"开启插件", actionPerformed=self.toggleSwitch)
        self.clear_button = JButton(u'清除日志', actionPerformed=self.clearOutput)
        self.load_from_text_button = JButton(u'加载代理', actionPerformed=self.loadProxiesFromText)
        self.request_count_label = JLabel(u"请求次数: ")
        self.request_count_field = JTextField("1", 5)

        # 添加HTTP地址输入框和获取代理按钮
        self.http_address_label = JLabel(u"URL地址: ")
        self.http_address_field = JTextField("http://192.168.1.202:5010/all/", 20)
        self.fetch_proxies_button = JButton(u'获取代理', actionPerformed=self.fetchProxies)

        # 代理类型选择
        self.radio_http = JRadioButton("HTTP", True)
        # self.radio_socks5 = JRadioButton("SOCKS5")
        self.radio_group = ButtonGroup()
        # self.radio_group.add(self.radio_socks5)
        self.radio_group.add(self.radio_http)
        
        # 将组件添加到顶部面板
        self.top_panel.add(self.toggle_plugin)
        self.top_panel.add(Box.createHorizontalStrut(20))
        self.top_panel.add(self.http_address_label)
        self.top_panel.add(self.http_address_field)
        self.top_panel.add(self.fetch_proxies_button)
        self.top_panel.add(self.load_from_text_button)
        self.top_panel.add(self.clear_button)
        self.top_panel.add(Box.createHorizontalStrut(20))
        self.top_panel.add(self.request_count_label)
        self.top_panel.add(self.request_count_field)
        self.top_panel.add(Box.createHorizontalStrut(20))
        self.top_panel.add(self.radio_http)
        # self.top_panel.add(self.radio_socks5)
        
        # 创建中部面板，包含两个子面板和分隔线
        self.middle_panel = JPanel()
        self.middle_panel.setLayout(BoxLayout(self.middle_panel, BoxLayout.X_AXIS))
        
        # 创建代理粘贴区域
        self.proxy_panel = JPanel()
        self.proxy_panel.setLayout(BorderLayout())
        self.proxy_label = JLabel(u"  Proxy Lists")
        self.proxy_text_area = JTextArea(10, 30)
        self.proxy_scroll_pane = JScrollPane(self.proxy_text_area)
        self.proxy_panel.add(self.proxy_label, BorderLayout.NORTH)
        self.proxy_panel.add(self.proxy_scroll_pane, BorderLayout.CENTER)
                
        # 添加空白区域
        separator_panel = JPanel()
        separator_panel.setBorder(EmptyBorder(0, 1, 0, 1))
        
        # 创建响应区域
        self.log_panel = JPanel()
        self.log_panel.setLayout(BorderLayout())
        self.log_label = JLabel(u"  Logs")
        self.response_area = JTextArea(10, 30)
        self.response_area.setEditable(False)
        self.scroll_pane = JScrollPane(self.response_area)
        self.log_panel.add(self.log_label, BorderLayout.NORTH)
        self.log_panel.add(self.scroll_pane, BorderLayout.CENTER)
        
        # 将代理粘贴区域和响应区域添加到中部面板
        self.middle_panel.add(self.proxy_panel)
        self.middle_panel.add(separator_panel)
        self.middle_panel.add(self.log_panel)
        
        # 将面板添加到主面板
        self.panel.add(self.top_panel, BorderLayout.NORTH)
        self.panel.add(self.middle_panel, BorderLayout.CENTER)
        
        # 初始化其他变量
        self.enabled = False
        self.proxies = []
        # 添加扩展的标签
        self._callbacks.addSuiteTab(self)
        
        # 打印信息
        print(u"Proxy Switcher loaded.")
        print(u"作者: gh0stNinja")
        print(u"GitHub: https://github.com/gh0stNinja")
        print(u"Blog: https://gh0stninja.github.io/")

    def getTabCaption(self):
        # 返回标签标题
        return u"Proxy Switcher"

    def getUiComponent(self):
        # 返回UI组件
        return self.panel

    def toggleSwitch(self, event):
        # 切换启用/禁用状态
        self.enabled = self.toggle_plugin.isSelected()
        if self.enabled:
            self.response_area.append(u"插件已启用\n")
        else:
            self.response_area.append(u"插件已关闭\n")

    def fetchProxies(self, event):
        if not self.enabled:
            return
        url = self.http_address_field.getText()
        if not url:
            self.response_area.append(u"请输入有效的HTTP地址。\n")
            return
        try:
            # 创建 HTTP 请求
            req = java.net.URL(url)
            connection = req.openConnection()
            connection.setRequestMethod("GET")
            connection.connect()
            inputStream = connection.getInputStream()
            response = self._helpers.bytesToString(inputStream.readAllBytes())
            proxies = json.loads(response)
            self.displayProxies(proxies)
        except Exception as e:
            self.response_area.append(u"获取代理时出错: {}\n".format(str(e)))

    def displayProxies(self, proxies):
        self.proxy_text_area.setText("")  # 清空当前内容
        for proxy in proxies:
            proxy_address = proxy.get('proxy', '')
            self.proxy_text_area.append("{}\n".format(proxy_address))
        self.response_area.append(u"代理已加载\n")

    def loadProxiesFromText(self, event=None):
        if not self.enabled:
            return
        self.proxies = []
        # 从文本区域加载代理
        proxy_text = self.proxy_text_area.getText()
        self.proxies = [line.strip() for line in proxy_text.split('\n') if line.strip()]
        self.response_area.append(u"Proxy List loaded.\n")

    def clearOutput(self, event):
        # 清除输出区域
        self.response_area.setText("")

    def processHttpMessage(self, toolFlag, messageIsRequest, messageInfo):
        # 如果插件未启用或消息不是请求，则返回
        if not self.enabled or not messageIsRequest:
            return
        # 如果请求来自Intruder或Repeater并且有可用的代理
        if toolFlag in (self._callbacks.TOOL_INTRUDER, self._callbacks.TOOL_REPEATER) and self.proxies:
            # 随机选择一个代理
            proxy = random.choice(self.proxies)
            host, port = proxy.split(":")
            # 根据选择的代理类型设置协议
            # if self.radio_socks5.isSelected():
            #     protocol = "socks"
            # else:
            protocol = "http"
            # 设置HTTP服务
            messageInfo.setHttpService(self._helpers.buildHttpService(host, int(port), protocol))
            # 在输出区域显示信息
            self.response_area.append("[ {} ] [ {} ] [ {}:{} ]\n".format(self._callbacks.getToolName(toolFlag), protocol.upper(), host, port))


# 主函数入口
def main():
    return BurpExtender()


# 如果直接执行该脚本，则调用 main 函数
if __name__ == "__main__":
    main()
