#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境变量设置助手脚本
"""

import os
import sys

def create_env_file():
    """创建.env文件"""
    
    print("🔧 加密货币交易信号机器人 - 环境配置助手")
    print("=" * 50)
    
    # 检查.env文件是否已存在
    if os.path.exists('.env'):
        response = input("⚠️  .env文件已存在，是否覆盖？ (y/N): ")
        if response.lower() != 'y':
            print("❌ 配置取消")
            return
    
    print("\n📝 请提供以下配置信息：")
    print("💡 提示：按回车键跳过可选配置项\n")
    
    # 获取Telegram Bot Token
    while True:
        bot_token = input("🤖 Telegram Bot Token (必填，从@BotFather获取): ").strip()
        if bot_token:
            break
        print("❌ Bot Token不能为空，请重新输入")
    
    # 可选配置
    log_level = input("📊 日志级别 (DEBUG/INFO/WARNING/ERROR) [默认INFO]: ").strip() or "INFO"
    
    # 创建.env文件内容
    env_content = f"""# Telegram机器人配置
TELEGRAM_BOT_TOKEN={bot_token}

# 日志配置
LOG_LEVEL={log_level}

# OKX API配置 (可选，用于增强功能)
# OKX_API_KEY=your_api_key_here
# OKX_SECRET_KEY=your_secret_key_here
# OKX_PASSPHRASE=your_passphrase_here

# 其他可选配置
# MAX_CONCURRENT_REQUESTS=10
# REQUEST_TIMEOUT=30
"""
    
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print("\n✅ 环境配置文件已创建！")
        print("📁 文件位置: .env")
        print("\n🔒 安全提示：")
        print("   • 请勿将.env文件提交到版本控制系统")
        print("   • 确保.env已添加到.gitignore文件中")
        print("   • 定期更换敏感Token")
        
        print("\n🚀 下一步操作：")
        print("   1. 安装依赖: pip install -r requirements.txt")
        print("   2. 启动机器人: python main.py")
        
    except Exception as e:
        print(f"\n❌ 创建配置文件失败: {e}")
        return False
    
    return True

def check_requirements():
    """检查Python版本和依赖"""
    
    print("\n🔍 环境检查...")
    
    # 检查Python版本
    py_version = sys.version_info
    if py_version < (3, 10):
        print(f"❌ Python版本过低: {py_version.major}.{py_version.minor}")
        print("   需要Python 3.10或更高版本")
        return False
    else:
        print(f"✅ Python版本: {py_version.major}.{py_version.minor}.{py_version.micro}")
    
    # 检查关键依赖
    required_packages = [
        'ccxt', 'telegram', 'pandas', 'numpy', 'aiohttp', 'requests'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} (未安装)")
    
    if missing_packages:
        print(f"\n⚠️  缺少依赖包: {', '.join(missing_packages)}")
        print("   请运行: pip install -r requirements.txt")
        return False
    
    print("\n✅ 所有依赖检查通过！")
    return True

def main():
    """主函数"""
    try:
        # 创建环境配置
        if not create_env_file():
            sys.exit(1)
        
        # 检查环境
        if not check_requirements():
            print("\n💡 建议先安装依赖再启动机器人")
        
        print("\n🎉 环境配置完成！")
        
    except KeyboardInterrupt:
        print("\n\n👋 配置已取消")
    except Exception as e:
        print(f"\n❌ 配置过程中出错: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 