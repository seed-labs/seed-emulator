#!/usr/bin/env python
"""
AI邮件模板和钓鱼页面生成器
集成OpenAI GPT来生成高质量的钓鱼内容
"""

import openai
import os
import re
import base64
from email import message_from_string
from email.policy import default
from typing import List, Dict, Optional
from config import OPENAI_API_KEY, OPENAI_BASE_URL, MAIL_TEMPLATE_DIR

class AIPhishingGenerator:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        
    def analyze_real_email(self, email_path: str) -> Dict:
        """分析真实邮件模板，提取关键信息"""
        with open(email_path, 'r', encoding='utf-8', errors='ignore') as f:
            email_content = f.read()
        
        try:
            # 解析邮件
            msg = message_from_string(email_content, policy=default)
            
            # 提取基本信息
            subject = msg.get('Subject', '')
            sender = msg.get('From', '')
            
            # 解码subject如果是编码的
            if '=?' in subject:
                from email.header import decode_header
                decoded = decode_header(subject)
                subject = ''.join([
                    part[0].decode(part[1]) if isinstance(part[0], bytes) and part[1] 
                    else str(part[0]) for part in decoded
                ])
            
            # 获取邮件正文
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True)
                        if isinstance(body, bytes):
                            body = body.decode('utf-8', errors='ignore')
                        break
                    elif part.get_content_type() == "text/html":
                        html_body = part.get_payload(decode=True)
                        if isinstance(html_body, bytes):
                            html_body = html_body.decode('utf-8', errors='ignore')
                        body = html_body  # 优先使用HTML
            else:
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    body = payload.decode('utf-8', errors='ignore')
                else:
                    body = str(payload)
            
            return {
                'subject': subject,
                'sender': sender,
                'body': body[:2000],  # 限制长度
                'content_type': 'html' if '<html' in body.lower() else 'text'
            }
        except Exception as e:
            print(f"解析邮件失败 {email_path}: {e}")
            return None
    
    def generate_phishing_email(self, 
                               campaign_type: str = "security_alert",
                               target_company: str = "企业",
                               reference_email: Optional[str] = None) -> Dict:
        """生成钓鱼邮件模板"""
        
        # 如果提供了参考邮件，先分析
        reference_info = ""
        if reference_email and os.path.exists(reference_email):
            ref_data = self.analyze_real_email(reference_email)
            if ref_data:
                reference_info = f"""
参考邮件信息：
- 主题: {ref_data['subject']}
- 发件人: {ref_data['sender']}
- 内容风格: {ref_data['content_type']}
- 部分内容: {ref_data['body'][:500]}...
"""
        
        # 系统提示词
        system_prompt = f"""你是一个专业的网络安全研究员，正在为合法的安全意识培训创建钓鱼邮件模板。

任务要求：
1. 创建一个看起来真实可信的钓鱼邮件
2. 针对{target_company}的员工
3. 钓鱼类型：{campaign_type}
4. 必须包含{{{{.URL}}}}作为钓鱼链接占位符
5. 邮件需要有紧迫感和说服力
6. 模仿真实企业通知的格式和语调

{reference_info}

请生成以下格式的响应：
SUBJECT: [邮件主题]
FROM: [发件人信息]
BODY_TYPE: [html/text]
BODY: [邮件正文，包含{{{{.URL}}}}链接]
"""
        
        user_prompt = f"""请为{target_company}生成一个{campaign_type}类型的钓鱼邮件模板。

钓鱼场景说明：
- security_alert: 安全警告类邮件
- system_update: 系统升级通知
- account_verification: 账户验证
- urgent_action: 紧急操作要求
- reward_notification: 奖励通知
- document_sharing: 文档分享

要求：
1. 邮件必须看起来来自可信的官方来源
2. 使用适当的公司术语和格式
3. 创造紧迫感，促使用户点击链接
4. 链接使用{{{{.URL}}}}占位符
5. 包含适当的免责声明或联系信息让邮件看起来更真实
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return self._parse_email_response(content)
            
        except Exception as e:
            print(f"生成邮件模板失败: {e}")
            return None
    
    def generate_landing_page(self, 
                             page_type: str = "login",
                             company_name: str = "企业",
                             style: str = "corporate",
                             advanced_attacks: bool = False) -> Dict:
        """生成钓鱼页面（支持高级攻击演示）"""
        
        if advanced_attacks:
            return self._generate_advanced_attack_page(page_type, company_name, style)
        
        system_prompt = f"""你是一个专业的前端开发者和网络安全研究员，正在为合法的安全意识培训创建钓鱼页面。

任务要求：
1. 创建一个看起来真实可信的钓鱼页面
2. 针对{company_name}的风格
3. 页面类型：{page_type}
4. 设计风格：{style}
5. 必须包含{{{{.Tracker}}}}作为Gophish追踪代码占位符
6. 必须包含表单来收集用户数据
7. 使用现代化的CSS和响应式设计
8. 页面需要看起来专业和可信

请生成完整的HTML页面，包含：
- 专业的CSS样式
- 响应式设计
- 表单验证
- 用户体验优化
- 适当的品牌元素
"""
        
        user_prompt = f"""请为{company_name}生成一个{page_type}类型的钓鱼页面。

页面类型说明：
- login: 登录页面
- verification: 身份验证页面  
- update_info: 信息更新页面
- security_check: 安全检查页面
- document_access: 文档访问页面
- survey: 调查问卷页面

设计要求：
1. 现代化的界面设计
2. 适当的公司logo和品牌色彩
3. 表单必须POST数据到当前页面
4. 包含{{{{.Tracker}}}}追踪代码
5. 使用{style}风格（corporate/modern/minimal）
6. 移动端兼容
7. 添加适当的loading和提示效果
8. 包含隐私政策或服务条款链接增加可信度

请返回完整的HTML代码。
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.6
            )
            
            html_content = response.choices[0].message.content
            
            # 清理代码块标记
            html_content = re.sub(r'```html\n?', '', html_content)
            html_content = re.sub(r'```\n?$', '', html_content)
            
            return {
                'name': f"{company_name}_{page_type}_{style}",
                'html': html_content,
                'capture_credentials': True,
                'capture_passwords': True
            }
            
        except Exception as e:
            print(f"生成钓鱼页面失败: {e}")
            return None
    
    def _generate_advanced_attack_page(self, page_type: str, company_name: str, style: str) -> Dict:
        """生成包含高级攻击演示的钓鱼页面"""
        
        # 读取高级攻击演示模板
        template_path = os.path.join(os.path.dirname(__file__), '..', '🎭高级钓鱼页面攻击演示.html')
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 根据公司名称定制页面
            if company_name.lower() == 'metamask' or 'metamask' in company_name.lower():
                # MetaMask样式已经在模板中
                customized_html = template_content
                page_name = f"高级MetaMask钓鱼演示_{style}"
            else:
                # 为其他公司定制
                customized_html = self._customize_attack_page(template_content, company_name, page_type, style)
                page_name = f"高级{company_name}钓鱼演示_{page_type}_{style}"
            
            return {
                'name': page_name,
                'html': customized_html,
                'capture_credentials': True,
                'capture_passwords': True,
                'advanced_attacks': True
            }
            
        except FileNotFoundError:
            print("高级攻击演示模板文件未找到，使用AI生成")
            return self._generate_ai_advanced_page(page_type, company_name, style)
        except Exception as e:
            print(f"加载高级攻击模板失败: {e}")
            return None
    
    def _customize_attack_page(self, template: str, company_name: str, page_type: str, style: str) -> str:
        """为不同公司定制高级攻击页面"""
        
        # 公司特定的品牌配色和样式
        company_configs = {
            'google': {
                'primary_color': '#4285f4',
                'secondary_color': '#34a853',
                'name': 'Google',
                'icon': '🔍'
            },
            'microsoft': {
                'primary_color': '#00bcf2',
                'secondary_color': '#0078d4',
                'name': 'Microsoft',
                'icon': '🪟'
            },
            'apple': {
                'primary_color': '#007aff',
                'secondary_color': '#5856d6',
                'name': 'Apple',
                'icon': '🍎'
            },
            'aws': {
                'primary_color': '#ff9900',
                'secondary_color': '#232f3e',
                'name': 'AWS',
                'icon': '☁️'
            }
        }
        
        config = company_configs.get(company_name.lower(), {
            'primary_color': '#007bff',
            'secondary_color': '#6c757d',
            'name': company_name,
            'icon': '🏢'
        })
        
        # 替换品牌元素
        customized = template.replace('MetaMask', config['name'])
        customized = customized.replace('🦊', config['icon'])
        customized = customized.replace('#f6851b', config['primary_color'])
        customized = customized.replace('#e2761b', config['secondary_color'])
        
        # 根据页面类型调整表单字段
        if page_type == 'login':
            form_fields = '''
                <div class="form-group">
                    <label>Email Address:</label>
                    <input type="email" name="email" id="email" required placeholder="Enter your email">
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" name="password" id="password" required placeholder="Enter your password">
                </div>
            '''
        elif page_type == 'verification':
            form_fields = '''
                <div class="form-group">
                    <label>Email Address:</label>
                    <input type="email" name="email" id="email" required placeholder="Enter your email">
                </div>
                <div class="form-group">
                    <label>Verification Code:</label>
                    <input type="text" name="code" id="code" required placeholder="Enter 6-digit code">
                </div>
                <div class="form-group">
                    <label>Backup Password:</label>
                    <input type="password" name="password" id="password" required placeholder="Enter backup password">
                </div>
            '''
        else:
            # 保持原有的MetaMask字段作为默认
            form_fields = None
        
        if form_fields:
            # 替换表单字段（这里需要更精确的正则表达式）
            import re
            form_pattern = r'<form method="post" id="credentialForm">.*?</form>'
            if re.search(form_pattern, customized, re.DOTALL):
                new_form = f'''<form method="post" id="credentialForm">
                    {form_fields}
                    <button type="submit" class="btn" id="submitBtn">🔐 Verify Account</button>
                </form>'''
                customized = re.sub(form_pattern, new_form, customized, flags=re.DOTALL)
        
        return customized
    
    def _generate_ai_advanced_page(self, page_type: str, company_name: str, style: str) -> Dict:
        """使用AI生成高级攻击演示页面"""
        
        system_prompt = """你是一个专业的网络安全研究员，正在创建一个用于安全意识培训的高级钓鱼页面演示。

这个页面需要展示真实的浏览器攻击技术，包括：
1. 标签页劫持 (Tab Nabbing)
2. 浏览器指纹识别
3. 键盘和鼠标监听
4. Cookie窃取
5. 会话劫持演示
6. 开发者工具检测
7. 恶意JavaScript执行
8. 数据外泄模拟

页面应该：
- 首先显示一个正常的钓鱼表单
- 在用户提交后，展示完整的攻击演示界面
- 模拟真实攻击者会执行的各种恶意操作
- 显示被窃取的数据和攻击进度
- 包含教育价值，让用户理解攻击的严重性

请生成完整的HTML+CSS+JavaScript代码。
"""
        
        user_prompt = f"""为{company_name}创建一个{page_type}类型的高级攻击演示页面，风格为{style}。

要求：
1. 模仿{company_name}的品牌设计
2. 包含{{{{.Tracker}}}}追踪代码
3. 表单收集凭据后展示攻击演示
4. 演示标签页劫持、Cookie窃取、指纹识别等攻击
5. 显示被窃取数据的可视化界面
6. 包含终端风格的攻击进度显示
7. 最后显示安全教育信息

这是用于合法的安全意识培训，展示真实攻击的危害。
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            
            html_content = response.choices[0].message.content
            
            # 清理代码块标记
            html_content = re.sub(r'```html\n?', '', html_content)
            html_content = re.sub(r'```\n?$', '', html_content)
            
            return {
                'name': f"AI高级攻击演示_{company_name}_{page_type}_{style}",
                'html': html_content,
                'capture_credentials': True,
                'capture_passwords': True,
                'advanced_attacks': True
            }
            
        except Exception as e:
            print(f"生成AI高级攻击页面失败: {e}")
            return None
    
    def _parse_email_response(self, content: str) -> Dict:
        """解析AI生成的邮件响应"""
        try:
            lines = content.strip().split('\n')
            result = {}
            
            current_key = None
            current_content = []
            
            for line in lines:
                if line.startswith('SUBJECT:'):
                    if current_key and current_content:
                        result[current_key.lower()] = '\n'.join(current_content).strip()
                    current_key = 'SUBJECT'
                    current_content = [line.replace('SUBJECT:', '').strip()]
                elif line.startswith('FROM:'):
                    if current_key and current_content:
                        result[current_key.lower()] = '\n'.join(current_content).strip()
                    current_key = 'FROM'
                    current_content = [line.replace('FROM:', '').strip()]
                elif line.startswith('BODY_TYPE:'):
                    if current_key and current_content:
                        result[current_key.lower()] = '\n'.join(current_content).strip()
                    current_key = 'BODY_TYPE'
                    current_content = [line.replace('BODY_TYPE:', '').strip()]
                elif line.startswith('BODY:'):
                    if current_key and current_content:
                        result[current_key.lower()] = '\n'.join(current_content).strip()
                    current_key = 'BODY'
                    current_content = [line.replace('BODY:', '').strip()]
                else:
                    if current_key:
                        current_content.append(line)
            
            # 添加最后一个键值对
            if current_key and current_content:
                result[current_key.lower()] = '\n'.join(current_content).strip()
            
            # 处理邮件模板格式
            template_data = {
                'name': f"AI生成_{result.get('subject', '未知主题')}",
                'subject': result.get('subject', '重要通知'),
                'from_address': result.get('from', 'noreply@company.com'),
                'text': result.get('body', ''),
                'html': result.get('body', '') if result.get('body_type', '').lower() == 'html' else ''
            }
            
            return template_data
            
        except Exception as e:
            print(f"解析邮件响应失败: {e}")
            return None
    
    def enhance_with_real_email(self, ai_template: Dict, reference_email_path: str) -> Dict:
        """使用真实邮件增强AI生成的模板"""
        if not os.path.exists(reference_email_path):
            return ai_template
        
        real_email = self.analyze_real_email(reference_email_path)
        if not real_email:
            return ai_template
        
        system_prompt = """你是一个专业的网络安全研究员。请将AI生成的钓鱼邮件模板与真实邮件的风格进行融合，
使生成的邮件更加真实可信。

要求：
1. 保持AI模板的核心钓鱼逻辑
2. 融合真实邮件的语言风格和格式
3. 保留{{.URL}}占位符
4. 确保邮件看起来更加专业和可信
"""
        
        user_prompt = f"""请将以下AI生成的邮件模板与真实邮件风格融合：

AI生成模板：
主题: {ai_template.get('subject', '')}
内容: {ai_template.get('text', '')}

真实邮件参考：
主题: {real_email.get('subject', '')}
发件人: {real_email.get('sender', '')}
内容片段: {real_email.get('body', '')[:1000]}

请生成融合后的邮件模板，格式与之前相同：
SUBJECT: [融合后的主题]
FROM: [改进的发件人]
BODY: [融合后的邮件正文]
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5
            )
            
            enhanced = self._parse_email_response(response.choices[0].message.content)
            return enhanced if enhanced else ai_template
            
        except Exception as e:
            print(f"增强邮件模板失败: {e}")
            return ai_template
    
    def get_available_real_emails(self) -> List[str]:
        """获取可用的真实邮件模板列表"""
        if not os.path.exists(MAIL_TEMPLATE_DIR):
            return []
        
        emails = []
        for file in os.listdir(MAIL_TEMPLATE_DIR):
            if file.endswith('.eml'):
                emails.append(os.path.join(MAIL_TEMPLATE_DIR, file))
        
        return emails
    
    def batch_generate_templates(self, scenarios: List[Dict]) -> List[Dict]:
        """批量生成邮件模板"""
        templates = []
        
        for scenario in scenarios:
            print(f"生成模板：{scenario['name']}")
            
            template = self.generate_phishing_email(
                campaign_type=scenario['type'],
                target_company=scenario.get('company', '企业'),
                reference_email=scenario.get('reference_email')
            )
            
            if template:
                template['name'] = scenario['name']
                templates.append(template)
            
        return templates

if __name__ == "__main__":
    # 测试AI生成器
    generator = AIPhishingGenerator()
    
    print("🤖 AI钓鱼内容生成器测试")
    print("=" * 50)
    
    # 测试邮件生成
    print("📧 生成邮件模板...")
    email_template = generator.generate_phishing_email(
        campaign_type="security_alert",
        target_company="XX科技公司"
    )
    
    if email_template:
        print(f"✅ 邮件模板生成成功")
        print(f"主题: {email_template['subject']}")
        print(f"内容预览: {email_template['text'][:200]}...")
    
    # 测试页面生成
    print("\n🌐 生成钓鱼页面...")
    landing_page = generator.generate_landing_page(
        page_type="login",
        company_name="XX科技公司",
        style="corporate"
    )
    
    if landing_page:
        print(f"✅ 钓鱼页面生成成功")
        print(f"页面名称: {landing_page['name']}")
        print(f"HTML长度: {len(landing_page['html'])} 字符")
    
    # 获取可用的真实邮件
    print("\n📬 可用的真实邮件模板:")
    real_emails = generator.get_available_real_emails()
    for i, email in enumerate(real_emails, 1):
        print(f"  {i}. {os.path.basename(email)}")
