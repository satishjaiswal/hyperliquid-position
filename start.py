#!/usr/bin/env python3
"""
Hyperliquid Position Monitor - Start Script
Automated setup and launch script with virtual environment management,
dependency installation, log management, and application startup.
"""

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path
from datetime import datetime

def print_banner():
    """Print startup banner"""
    print("=" * 60)
    print("🚀 HYPERLIQUID POSITION MONITOR")
    print("=" * 60)
    print("📦 Automated Setup & Launch Script")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

def clear_logs():
    """Clear existing logs with user confirmation"""
    logs_dir = Path("logs")
    
    if logs_dir.exists() and any(logs_dir.iterdir()):
        print("\n🗑️  Log Management")
        print("-" * 30)
        
        # Count existing log files
        log_files = list(logs_dir.glob("*.log"))
        print(f"Found {len(log_files)} existing log files")
        
        if log_files:
            for log_file in log_files[:5]:  # Show first 5 files
                size_kb = log_file.stat().st_size / 1024
                print(f"  • {log_file.name} ({size_kb:.1f} KB)")
            
            if len(log_files) > 5:
                print(f"  • ... and {len(log_files) - 5} more files")
        
        response = input("\n🤔 Clear existing logs? (y/N): ").strip().lower()
        
        if response == 'y':
            try:
                shutil.rmtree(logs_dir)
                print("✅ Logs cleared successfully")
            except Exception as e:
                print(f"❌ Error clearing logs: {e}")
        else:
            print("📁 Keeping existing logs")
    
    # Ensure logs directory exists
    logs_dir.mkdir(exist_ok=True)
    print("📁 Logs directory ready")

def get_python_executable():
    """Get the appropriate Python executable"""
    # Try different Python executable names
    python_names = ['python', 'python3', 'py']
    
    for name in python_names:
        try:
            result = subprocess.run([name, '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"🐍 Found Python: {name} ({version})")
                return name
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    print("❌ Python not found in PATH")
    sys.exit(1)

def setup_virtual_environment():
    """Setup virtual environment if it doesn't exist"""
    venv_dir = Path("venv")
    python_exe = get_python_executable()
    
    print("\n🏗️  Virtual Environment Setup")
    print("-" * 30)
    
    if venv_dir.exists():
        print("✅ Virtual environment already exists")
        return
    
    print("📦 Creating virtual environment...")
    try:
        subprocess.run([python_exe, '-m', 'venv', 'venv'], 
                      check=True, timeout=60)
        print("✅ Virtual environment created successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create virtual environment: {e}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("❌ Virtual environment creation timed out")
        sys.exit(1)

def get_venv_python():
    """Get the Python executable from virtual environment"""
    system = platform.system().lower()
    
    if system == "windows":
        return Path("venv/Scripts/python.exe")
    else:
        return Path("venv/bin/python")

def get_venv_pip():
    """Get the pip executable from virtual environment"""
    system = platform.system().lower()
    
    if system == "windows":
        return Path("venv/Scripts/pip.exe")
    else:
        return Path("venv/bin/pip")

def install_dependencies():
    """Install or upgrade dependencies"""
    print("\n📥 Dependency Management")
    print("-" * 30)
    
    pip_exe = get_venv_pip()
    
    if not pip_exe.exists():
        print(f"❌ Pip not found at: {pip_exe}")
        sys.exit(1)
    
    requirements_file = Path("requirements.txt")
    if not requirements_file.exists():
        print("❌ requirements.txt not found")
        sys.exit(1)
    
    print("📦 Installing/upgrading dependencies...")
    try:
        # Try to upgrade pip (ignore if it fails on Windows)
        try:
            subprocess.run([str(pip_exe), 'install', '--upgrade', 'pip'], 
                          check=True, timeout=120)
            print("✅ Pip upgraded successfully")
        except subprocess.CalledProcessError:
            print("⚠️ Pip upgrade skipped (Windows restriction)")
        
        # Install requirements
        subprocess.run([str(pip_exe), 'install', '-r', 'requirements.txt', '--upgrade'], 
                      check=True, timeout=300)
        
        print("✅ Dependencies installed successfully")
        
        # Show installed packages
        print("\n📋 Installed packages:")
        result = subprocess.run([str(pip_exe), 'list'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')[2:]  # Skip header
            for line in lines[:10]:  # Show first 10 packages
                if line.strip():
                    print(f"  • {line}")
            
            if len(lines) > 10:
                print(f"  • ... and {len(lines) - 10} more packages")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("❌ Dependency installation timed out")
        sys.exit(1)

def validate_environment():
    """Validate environment variables"""
    print("\n🔍 Environment Validation")
    print("-" * 30)
    
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found")
        print("📝 Please create .env file using .env.example as template")
        sys.exit(1)
    
    # Load and check environment variables
    required_vars = ['HL_WALLET_ADDRESS', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
    missing_vars = []
    
    try:
        with open(env_file, 'r') as f:
            env_content = f.read()
        
        for var in required_vars:
            if f"{var}=" not in env_content or f"{var}=your_" in env_content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing or incomplete environment variables:")
            for var in missing_vars:
                print(f"  • {var}")
            print("\n📝 Please update your .env file with actual values")
            sys.exit(1)
        
        print("✅ Environment variables validated")
        
    except Exception as e:
        print(f"❌ Error validating environment: {e}")
        sys.exit(1)

def test_connectivity():
    """Test basic connectivity"""
    print("\n🌐 Connectivity Test")
    print("-" * 30)
    
    try:
        import requests
        
        # Test Hyperliquid API
        print("📡 Testing Hyperliquid API...")
        response = requests.get("https://api.hyperliquid.xyz/info", timeout=10)
        if response.status_code == 200:
            print("✅ Hyperliquid API accessible")
        else:
            print(f"⚠️ Hyperliquid API returned status: {response.status_code}")
        
        # Test Telegram API
        print("📱 Testing Telegram API...")
        response = requests.get("https://api.telegram.org", timeout=10)
        if response.status_code == 200:
            print("✅ Telegram API accessible")
        else:
            print(f"⚠️ Telegram API returned status: {response.status_code}")
            
    except ImportError:
        print("⚠️ Requests module not available for connectivity test")
    except Exception as e:
        print(f"⚠️ Connectivity test failed: {e}")
        print("🔄 Continuing anyway...")

def launch_application():
    """Launch the main application"""
    print("\n🚀 Application Launch")
    print("-" * 30)
    
    python_exe = get_venv_python()
    
    if not python_exe.exists():
        print(f"❌ Python executable not found at: {python_exe}")
        sys.exit(1)
    
    app_file = Path("send_positions.py")
    if not app_file.exists():
        print("❌ send_positions.py not found")
        sys.exit(1)
    
    print("🎯 Starting Hyperliquid Position Monitor...")
    print("💡 Use Ctrl+C to stop the application")
    print("=" * 60)
    
    try:
        # Launch the application
        subprocess.run([str(python_exe), 'send_positions.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Application exited with error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

def main():
    """Main setup and launch sequence"""
    try:
        print_banner()
        
        # Setup sequence
        clear_logs()
        setup_virtual_environment()
        install_dependencies()
        validate_environment()
        test_connectivity()
        
        print("\n🎉 Setup completed successfully!")
        print("=" * 60)
        
        # Launch application
        launch_application()
        
    except KeyboardInterrupt:
        print("\n\n👋 Setup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error during setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
