#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import requests
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

class ElonSummaryMonitor:
    def __init__(self, repo_path, webhook_url):
        """
        初始化监控器
        
        Args:
            repo_path: 本地仓库路径
            webhook_url: 企业微信机器人 webhook URL
        """
        self.repo_path = Path(repo_path)
        self.webhook_url = webhook_url
        self.last_check_file = Path("last_check.json")
        self.load_last_check()
    
    def load_last_check(self):
        """加载上次检查的时间"""
        if self.last_check_file.exists():
            with open(self.last_check_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.last_check_time = datetime.fromisoformat(data.get('last_check', '2025-01-01T00:00:00'))
        else:
            self.last_check_time = datetime.now() - timedelta(days=1)
    
    def save_last_check(self):
        """保存本次检查的时间"""
        with open(self.last_check_file, 'w', encoding='utf-8') as f:
            json.dump({
                'last_check': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
    
    def git_pull(self):
        """拉取最新代码"""
        try:
            result = subprocess.run(
                ['git', 'pull', 'origin', 'master'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def get_new_summaries(self):
        """获取新的总结文件"""
        new_summaries = []
        
        # 查找所有 markdown 文件
        for md_file in self.repo_path.glob("*.md"):
            # 检查文件修改时间
            file_mtime = datetime.fromtimestamp(md_file.stat().st_mtime)
            
            if file_mtime > self.last_check_time:
                try:
                    with open(md_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_summaries.append({
                        'filename': md_file.name,
                        'content': content,
                        'modified_time': file_mtime.isoformat()
                    })
                except Exception as e:
                    print(f"读取文件 {md_file} 失败: {e}")
        
        return new_summaries
    
    def send_to_wechat(self, summary_data):
        """发送到企业微信机器人"""
        try:
            # 构造消息内容
            filename = summary_data['filename']
            content = summary_data['content']
            
            # 构造消息内容，使用你提供的API格式
            message = f"{content}"
            
            # 企业微信机器人消息格式
            data = {
                "msgContent": message,
                "botKey": os.getenv("WECHAT_BOT_KEY"),
                "multiGroupMode": 1,
            }
            
            # 发送请求
            response = requests.post(
                self.webhook_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('retCode') == 200:
                    print(f"✅ 成功发送到企业微信: {filename}")
                    return True
                else:
                    print(f"❌ 企业微信返回错误: {result}")
                    return False
            else:
                print(f"❌ HTTP 请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ 发送到企业微信失败: {e}")
            return False
    
    def run(self):
        """运行监控"""
        print(f"🔍 开始检查 Elon 总结更新...")
        print(f"📁 仓库路径: {self.repo_path}")
        print(f"⏰ 上次检查: {self.last_check_time}")
        
        # 拉取最新代码
        success, stdout, stderr = self.git_pull()
        if not success:
            print(f"❌ Git pull 失败: {stderr}")
            return
        
        if "Already up to date" in stdout:
            print("📋 仓库已是最新版本")
        else:
            print("📥 已拉取最新代码")
        
        # 获取新的总结文件
        new_summaries = self.get_new_summaries()
        
        if not new_summaries:
            print("📭 没有发现新的总结文件")
        else:
            print(f"📄 发现 {len(new_summaries)} 个新的总结文件")
            
            # 发送每个新文件
            for summary in new_summaries:
                print(f"📤 正在发送: {summary['filename']}")
                self.send_to_wechat(summary)
                time.sleep(1)  # 避免发送过快
        
        # 保存检查时间
        self.save_last_check()
        print("✅ 检查完成")

def main():
    # 配置参数
    REPO_PATH = "./elon-daily-summaries"  # 本地仓库路径
    WEBHOOK_URL = os.getenv("WECHAT_WEBHOOK_URL")
    
    # 检查必要的环境变量
    bot_key = os.getenv("WECHAT_BOT_KEY")
    if not bot_key:
        print("❌ 请设置环境变量 WECHAT_BOT_KEY")
        print("例如: export WECHAT_BOT_KEY='你的企业微信机器人key'")
        return
    
    # 检查仓库路径
    if not os.path.exists(REPO_PATH):
        print(f"❌ 仓库路径不存在: {REPO_PATH}")
        return
    
    # 创建监控器并运行
    monitor = ElonSummaryMonitor(REPO_PATH, WEBHOOK_URL)
    monitor.run()

if __name__ == "__main__":
    main() 