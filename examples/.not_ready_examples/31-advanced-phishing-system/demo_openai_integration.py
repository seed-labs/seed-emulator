#!/usr/bin/env python3
"""
31-advanced-phishing-system OpenAI集成演示脚本
展示OpenAI各种模型的使用和钓鱼内容生成能力
"""

import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

class OpenAIDemo:
    def __init__(self):
        self.client = None
        self.models_tested = []
        self.results = []

        # 初始化OpenAI客户端
        if os.getenv('OPENAI_API_KEY'):
            try:
                self.client = OpenAI(
                    api_key=os.getenv('OPENAI_API_KEY'),
                    base_url=os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
                )
                print("✅ OpenAI客户端初始化成功")
            except Exception as e:
                print(f"❌ OpenAI客户端初始化失败: {str(e)}")
                self.client = None

    async def test_openai_connection(self):
        """测试OpenAI连接"""
        print("\n🤖 测试OpenAI连接...")

        if not self.client:
            print("❌ OpenAI客户端未初始化")
            return False

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Hello, can you confirm you're working?"}],
                    max_tokens=50
                )
            )

            if response and response.choices:
                print(f"✅ OpenAI连接测试成功: {response.choices[0].message.content.strip()}")
                return True
            else:
                print("❌ OpenAI响应为空")
                return False

        except Exception as e:
            print(f"❌ OpenAI连接测试失败: {str(e)}")
            return False

    async def test_available_models(self):
        """测试可用模型"""
        print("\n📋 测试可用模型...")

        models_to_test = [
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-3.5-turbo-16k"
        ]

        for model in models_to_test:
            try:
                print(f"  测试 {model}...")

                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": f"Respond with 'OK' if you are {model}"}],
                        max_tokens=10
                    )
                )

                if response and response.choices:
                    self.models_tested.append({
                        "model": model,
                        "status": "available",
                        "response": response.choices[0].message.content.strip()
                    })
                    print(f"    ✅ {model} 可用")
                else:
                    print(f"    ❌ {model} 无响应")

            except Exception as e:
                print(f"    ⚠️  {model} 不可用: {str(e)}")
                self.models_tested.append({
                    "model": model,
                    "status": "unavailable",
                    "error": str(e)
                })

    async def generate_phishing_content_demo(self):
        """钓鱼内容生成演示"""
        print("\n🎣 钓鱼内容生成演示...")

        prompts = [
            {
                "type": "企业钓鱼",
                "prompt": """生成一封针对企业IT管理员的钓鱼邮件，要求他们点击链接验证系统安全设置。

目标信息:
- 姓名: 张三
- 职位: IT管理员
- 公司: ABC科技有限公司

要求:
1. 使用正式的企业邮件风格
2. 包含合理的紧急性和重要性
3. 添加可信的公司细节
4. 避免明显的钓鱼特征
5. 包含适当的问候和签名""",
                "model": "gpt-4o"
            },
            {
                "type": "高管钓鱼",
                "prompt": """生成一封针对CEO的紧急通知邮件，要求立即处理重要事务。

目标信息:
- 姓名: 李总
- 职位: CEO
- 公司: XYZ集团

要求:
1. 使用高管邮件的正式语气
2. 强调紧急性和重要性
3. 包含具体的行动要求
4. 使用专业的企业术语
5. 提供合理的联系方式""",
                "model": "gpt-4-turbo"
            },
            {
                "type": "个人钓鱼",
                "prompt": """生成一封看似来自朋友的个人邮件。

目标信息:
- 姓名: 小明
- 关系: 大学同学

要求:
1. 使用亲切的个人语气
2. 包含个人化的细节
3. 提及共同的经历或兴趣
4. 自然地引导点击链接
5. 避免商业化特征""",
                "model": "gpt-3.5-turbo"
            }
        ]

        for prompt_data in prompts:
            print(f"\n📧 生成 {prompt_data['type']} 内容...")
            print(f"🤖 使用模型: {prompt_data['model']}")

            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=prompt_data['model'],
                        messages=[{"role": "user", "content": prompt_data['prompt']}],
                        max_tokens=1000,
                        temperature=0.7
                    )
                )

                if response and response.choices:
                    content = response.choices[0].message.content.strip()
                    tokens_used = response.usage.total_tokens if response.usage else "N/A"

                    print(f"✅ 生成成功 ({tokens_used} tokens)")
                    print(f"📝 生成内容预览:")
                    print("-" * 50)
                    # 只显示前200个字符作为预览
                    preview = content[:200] + "..." if len(content) > 200 else content
                    print(preview)
                    print("-" * 50)

                    self.results.append({
                        "type": prompt_data['type'],
                        "model": prompt_data['model'],
                        "content": content,
                        "tokens_used": tokens_used,
                        "timestamp": datetime.now().isoformat()
                    })

                else:
                    print("❌ 生成失败: 无响应内容")

            except Exception as e:
                print(f"❌ 生成失败: {str(e)}")

            # 短暂延迟避免API限制
            await asyncio.sleep(1)

    async def analyze_threat_demo(self):
        """威胁分析演示"""
        print("\n🔍 威胁分析演示...")

        test_content = """
紧急安全通知

尊敬的用户：

我们的系统检测到您的账户存在异常登录活动。为了保护您的账户安全，请立即点击以下链接验证您的身份信息：

[安全验证链接] https://secure-bank-login.com/verify?user=john_doe

此链接将在24小时后过期。如果您没有进行任何登录操作，请忽略此邮件。

感谢您的配合！

安全团队
ABC银行
        """

        print("📄 分析内容:")
        print("-" * 50)
        print(test_content.strip())
        print("-" * 50)

        analysis_prompt = f"""
请分析以下邮件内容是否为钓鱼攻击，并提供详细的检测报告：

邮件内容:
{test_content}

请从以下方面分析:
1. 钓鱼特征识别
2. 风险等级评估
3. 可疑元素识别
4. 检测置信度
5. 建议的防护措施

请提供专业的安全分析报告。
"""

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": analysis_prompt}],
                    max_tokens=1500,
                    temperature=0.3
                )
            )

            if response and response.choices:
                analysis = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if response.usage else "N/A"

                print("✅ 威胁分析完成")
                print("-" * 50)
                print(analysis)
                print("-" * 50)
                print(f"📊 Token使用: {tokens_used}")

                self.results.append({
                    "type": "threat_analysis",
                    "model": "gpt-4o",
                    "analysis": analysis,
                    "tokens_used": tokens_used,
                    "timestamp": datetime.now().isoformat()
                })

        except Exception as e:
            print(f"❌ 威胁分析失败: {str(e)}")

    async def evasion_techniques_demo(self):
        """规避技术演示"""
        print("\n🛡️ 规避技术演示...")

        original_content = "紧急通知：您的账户存在安全风险，请立即点击验证链接处理。"

        print("📝 原始内容:")
        print(f"  {original_content}")

        evasion_prompt = f"""
请对以下钓鱼邮件内容应用规避技术，使其更难被检测系统识别：

原始内容: {original_content}

目标: 企业员工

规避要求:
1. 避免使用常见的钓鱼关键词 ("紧急", "立即", "验证")
2. 使用更自然的语言表达
3. 添加合理的上下文信息
4. 调整句子结构和长度
5. 包含可信的细节

请提供优化后的内容和使用的规避技术说明。
"""

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": evasion_prompt}],
                    max_tokens=800,
                    temperature=0.6
                )
            )

            if response and response.choices:
                optimized_content = response.choices[0].message.content.strip()
                tokens_used = response.usage.total_tokens if response.usage else "N/A"

                print("✅ 规避优化完成")
                print("📝 优化后内容:")
                print(f"  {optimized_content}")
                print(f"📊 Token使用: {tokens_used}")

                self.results.append({
                    "type": "evasion_demo",
                    "original": original_content,
                    "optimized": optimized_content,
                    "tokens_used": tokens_used,
                    "timestamp": datetime.now().isoformat()
                })

        except Exception as e:
            print(f"❌ 规避技术演示失败: {str(e)}")

    def save_results(self):
        """保存演示结果"""
        if self.results:
            result_file = f"openai_demo_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "demo_timestamp": datetime.now().isoformat(),
                    "openai_config": {
                        "api_key_configured": bool(os.getenv('OPENAI_API_KEY')),
                        "base_url": os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
                        "models_tested": len(self.models_tested)
                    },
                    "models_status": self.models_tested,
                    "demo_results": self.results
                }, f, indent=2, ensure_ascii=False)

            print(f"\n💾 演示结果已保存至: {result_file}")

    async def run_complete_demo(self):
        """运行完整演示"""
        print("🎭" + "="*60)
        print("        SEED 31项目 OpenAI集成演示")
        print("🎭" + "="*60)
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 1. 测试连接
        connection_ok = await self.test_openai_connection()
        if not connection_ok:
            print("❌ OpenAI连接失败，演示终止")
            return

        # 2. 测试可用模型
        await self.test_available_models()

        # 3. 钓鱼内容生成演示
        await self.generate_phishing_content_demo()

        # 4. 威胁分析演示
        await self.analyze_threat_demo()

        # 5. 规避技术演示
        await self.evasion_techniques_demo()

        # 保存结果
        self.save_results()

        print("\n🎭" + "="*60)
        print("                 演示完成")
        print("🎭" + "="*60)
        print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 成功演示项目: {len(self.results)}")
        print(f"🤖 测试模型数量: {len(self.models_tested)}")

        print("\n🎯 演示结果总结:")
        for result in self.results:
            print(f"  ✅ {result['type']} - {result.get('model', 'N/A')} ({result.get('tokens_used', 'N/A')} tokens)")

        print("\n🚀 OpenAI集成状态:")
        available_models = [m for m in self.models_tested if m['status'] == 'available']
        print(f"  📋 可用模型: {len(available_models)}个")
        for model in available_models:
            print(f"    • {model['model']}")

        print("\n💡 建议:")
        print("  • 在Web界面中使用OpenAI控制台进行交互式演示")
        print("  • 访问 http://localhost:5003/openai_console 体验完整功能")
        print("  • 可以配置不同的模型参数来优化生成效果")

async def main():
    """主函数"""
    demo = OpenAIDemo()
    await demo.run_complete_demo()

if __name__ == "__main__":
    print("🚀 启动OpenAI集成演示...")
    print("⚠️  请确保已正确配置OPENAI_API_KEY和OPENAI_BASE_URL环境变量")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 用户中断演示")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {str(e)}")
        print("💡 请检查网络连接和API配置")
