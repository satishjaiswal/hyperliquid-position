#!/usr/bin/env python3
"""
Startup script for Hyperliquid Position Monitor.
Handles environment setup, dependency installation, and service execution.
"""

import os
import sys
import subprocess
import shutil
import platform
from pathlib import Path


class HyperliquidStarter:
    """Handles the complete startup process for the Hyperliquid Position Monitor."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.venv_path = self.project_root / "venv"
        self.logs_path = self.project_root / "logs"
        self.requirements_file = self.project_root / "requirements.txt"
        self.env_file = self.project_root / ".env"
        self.env_example = self.project_root / ".env.example"
        
        # Platform-specific settings
        self.is_windows = platform.system() == "Windows"
        self.python_cmd = "python" if self.is_windows else "python3"
        self.pip_cmd = "pip" if self.is_windows else "pip3"
        
        if self.is_windows:
            self.venv_python = self.venv_path / "Scripts" / "python.exe"
            self.venv_pip = self.venv_path / "Scripts" / "pip.exe"
            self.activate_script = self.venv_path / "Scripts" / "activate.bat"
        else:
            self.venv_python = self.venv_path / "bin" / "python"
            self.venv_pip = self.venv_path / "bin" / "pip"
            self.activate_script = self.venv_path / "bin" / "activate"
    
    def print_header(self):
        """Print startup header."""
        print("=" * 60)
        print("🚀 Hyperliquid Position Monitor - Startup Script")
        print("=" * 60)
        print()
    
    def print_step(self, step: str, description: str = ""):
        """Print a step with formatting."""
        print(f"📋 {step}")
        if description:
            print(f"   {description}")
        print()
    
    def print_success(self, message: str):
        """Print success message."""
        print(f"✅ {message}")
        print()
    
    def print_error(self, message: str):
        """Print error message."""
        print(f"❌ {message}")
        print()
    
    def print_warning(self, message: str):
        """Print warning message."""
        print(f"⚠️ {message}")
        print()
    
    def check_python_version(self):
        """Check if Python version is compatible."""
        self.print_step("Checking Python version...")
        
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            self.print_error(f"Python 3.8+ required, found {version.major}.{version.minor}")
            sys.exit(1)
        
        self.print_success(f"Python {version.major}.{version.minor}.{version.micro} detected")
    
    def clear_logs(self):
        """Clear existing log files."""
        self.print_step("Clearing log files...")
        
        if self.logs_path.exists():
            try:
                # Remove all log files
                for log_file in self.logs_path.glob("*.log*"):
                    log_file.unlink()
                    print(f"   Removed: {log_file.name}")
                
                self.print_success("Log files cleared")
            except Exception as e:
                self.print_warning(f"Could not clear some log files: {e}")
        else:
            print("   No logs directory found")
            print()
    
    def create_venv(self):
        """Create virtual environment if it doesn't exist."""
        self.print_step("Checking virtual environment...")
        
        if self.venv_path.exists() and self.venv_python.exists():
            self.print_success("Virtual environment already exists")
            return
        
        print("   Creating new virtual environment...")
        try:
            # Remove existing venv if corrupted
            if self.venv_path.exists():
                shutil.rmtree(self.venv_path)
            
            # Create new virtual environment
            subprocess.run([
                self.python_cmd, "-m", "venv", str(self.venv_path)
            ], check=True, capture_output=True)
            
            self.print_success("Virtual environment created")
            
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to create virtual environment: {e}")
            sys.exit(1)
        except Exception as e:
            self.print_error(f"Unexpected error creating virtual environment: {e}")
            sys.exit(1)
    
    def upgrade_pip(self):
        """Upgrade pip in virtual environment."""
        self.print_step("Upgrading pip...")
        
        try:
            subprocess.run([
                str(self.venv_python), "-m", "pip", "install", "--upgrade", "pip"
            ], check=True, capture_output=True)
            
            self.print_success("Pip upgraded successfully")
            
        except subprocess.CalledProcessError as e:
            self.print_warning(f"Could not upgrade pip: {e}")
    
    def install_requirements(self):
        """Install Python packages from requirements.txt."""
        self.print_step("Installing Python packages...")
        
        if not self.requirements_file.exists():
            self.print_error("requirements.txt not found")
            sys.exit(1)
        
        try:
            # Install requirements
            result = subprocess.run([
                str(self.venv_python), "-m", "pip", "install", "-r", str(self.requirements_file)
            ], check=True, capture_output=True, text=True)
            
            self.print_success("All packages installed successfully")
            
        except subprocess.CalledProcessError as e:
            self.print_error(f"Failed to install packages: {e}")
            if e.stdout:
                print("STDOUT:", e.stdout)
            if e.stderr:
                print("STDERR:", e.stderr)
            sys.exit(1)
    
    def check_environment_file(self):
        """Check and create .env file if needed."""
        self.print_step("Checking environment configuration...")
        
        if not self.env_file.exists():
            if self.env_example.exists():
                print("   Creating .env from .env.example...")
                shutil.copy2(self.env_example, self.env_file)
                self.print_warning("Please edit .env file with your actual values before running")
                self.print_configuration_help()
                return False
            else:
                self.print_error(".env.example file not found")
                sys.exit(1)
        
        # Load and check environment variables using dotenv
        try:
            from dotenv import load_dotenv
            load_dotenv(self.env_file)
            
            # Check required variables
            required_vars = ['HL_WALLET_ADDRESS', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID']
            missing_vars = []
            placeholder_vars = []
            
            for var in required_vars:
                value = os.environ.get(var)
                if not value:
                    missing_vars.append(var)
                elif value.startswith('your_') or 'example' in value.lower():
                    placeholder_vars.append(var)
            
            if missing_vars or placeholder_vars:
                if missing_vars:
                    self.print_warning(f"Missing variables: {', '.join(missing_vars)}")
                if placeholder_vars:
                    self.print_warning(f"Placeholder values found: {', '.join(placeholder_vars)}")
                self.print_configuration_help()
                return False
            
            self.print_success("Environment configuration validated successfully")
            return True
            
        except ImportError:
            self.print_error("python-dotenv package not found. Installing...")
            return False
        except Exception as e:
            self.print_error(f"Could not validate .env file: {e}")
            return False
    
    def print_configuration_help(self):
        """Print help for configuring the environment."""
        print()
        print("📝 Configuration Required:")
        print("   Edit the .env file with your actual values:")
        print()
        print("   HL_WALLET_ADDRESS=your_actual_wallet_address")
        print("   TELEGRAM_BOT_TOKEN=your_actual_bot_token")
        print("   TELEGRAM_CHAT_ID=your_actual_chat_id")
        print()
        print("💡 How to get these values:")
        print("   • Wallet Address: Your Hyperliquid wallet address")
        print("   • Bot Token: Create a bot with @BotFather on Telegram")
        print("   • Chat ID: Send a message to @userinfobot on Telegram")
        print()
    
    def activate_venv_and_run(self):
        """Activate virtual environment and run the application."""
        self.print_step("Activating virtual environment and starting application...")
        
        try:
            # Change to project directory
            os.chdir(self.project_root)
            
            # Prepare environment with virtual environment activated
            env = os.environ.copy()
            
            # Add virtual environment to PATH
            if self.is_windows:
                venv_scripts = str(self.venv_path / "Scripts")
                env["PATH"] = f"{venv_scripts}{os.pathsep}{env.get('PATH', '')}"
            else:
                venv_bin = str(self.venv_path / "bin")
                env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
            
            # Set VIRTUAL_ENV environment variable
            env["VIRTUAL_ENV"] = str(self.venv_path)
            
            # Remove PYTHONHOME if it exists (can interfere with venv)
            env.pop("PYTHONHOME", None)
            
            # Add src to Python path
            src_path = str(self.project_root / "src")
            if "PYTHONPATH" in env:
                env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
            else:
                env["PYTHONPATH"] = src_path
            
            print("   Virtual environment activated")
            print(f"   Using Python: {self.venv_python}")
            print()
            
            # Run the application with activated environment
            subprocess.run([
                str(self.venv_python), "run.py"
            ], env=env, check=True)
            
        except subprocess.CalledProcessError as e:
            self.print_error(f"Application failed to start: {e}")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n🛑 Application interrupted by user")
        except Exception as e:
            self.print_error(f"Unexpected error: {e}")
            sys.exit(1)
    
    def run_application(self):
        """Run the main application (legacy method for compatibility)."""
        self.activate_venv_and_run()
    
    def print_manual_activation_help(self):
        """Print help for manual virtual environment activation."""
        print()
        print("🔧 Manual Virtual Environment Activation:")
        if self.is_windows:
            print(f"   {self.activate_script}")
        else:
            print(f"   source {self.activate_script}")
        print()
        print("Then run:")
        print("   python run.py")
        print()
    
    def print_activation_instructions(self):
        """Print instructions for activating the virtual environment."""
        self.print_success("Virtual environment setup complete!")
        print("🔧 To activate the virtual environment manually:")
        print()
        if self.is_windows:
            print(f"   {self.activate_script}")
        else:
            print(f"   source {self.activate_script}")
        print()
        print("📋 Available commands after activation:")
        print("   python run.py          # Run the position monitor")
        print("   python -m pip list     # List installed packages")
        print("   python -m pip install <package>  # Install additional packages")
        print()
        print("💡 To deactivate the virtual environment:")
        print("   deactivate")
        print()
    
    def start_interactive_shell(self):
        """Start an interactive shell with virtual environment activated."""
        self.print_step("Starting interactive shell with virtual environment...")
        
        try:
            # Prepare environment with virtual environment activated
            env = os.environ.copy()
            
            # Add virtual environment to PATH
            if self.is_windows:
                venv_scripts = str(self.venv_path / "Scripts")
                env["PATH"] = f"{venv_scripts}{os.pathsep}{env.get('PATH', '')}"
                shell_cmd = ["cmd.exe"]
            else:
                venv_bin = str(self.venv_path / "bin")
                env["PATH"] = f"{venv_bin}{os.pathsep}{env.get('PATH', '')}"
                shell_cmd = [env.get("SHELL", "/bin/bash")]
            
            # Set VIRTUAL_ENV environment variable
            env["VIRTUAL_ENV"] = str(self.venv_path)
            
            # Remove PYTHONHOME if it exists (can interfere with venv)
            env.pop("PYTHONHOME", None)
            
            # Add src to Python path
            src_path = str(self.project_root / "src")
            if "PYTHONPATH" in env:
                env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env['PYTHONPATH']}"
            else:
                env["PYTHONPATH"] = src_path
            
            # Change to project directory
            os.chdir(self.project_root)
            
            print("   Virtual environment activated")
            print(f"   Using Python: {self.venv_python}")
            print("   Type 'exit' to close the shell")
            print()
            
            # Start interactive shell
            subprocess.run(shell_cmd, env=env)
            
        except KeyboardInterrupt:
            print("\n🛑 Shell interrupted by user")
        except Exception as e:
            self.print_error(f"Failed to start interactive shell: {e}")
    
    def run(self):
        """Run the complete startup process."""
        try:
            self.print_header()
            
            # Step 1: Check Python version
            self.check_python_version()
            
            # Step 2: Clear logs
            self.clear_logs()
            
            # Step 3: Create/check virtual environment
            self.create_venv()
            
            # Step 4: Upgrade pip
            self.upgrade_pip()
            
            # Step 5: Install requirements
            self.install_requirements()
            
            # Step 6: Check environment configuration
            env_ready = self.check_environment_file()
            
            if not env_ready:
                print("⏸️  Setup complete, but configuration needed.")
                print("   Please update your .env file and run this script again.")
                self.print_manual_activation_help()
                return
            
            # Step 7: Run the application
            print("🎉 Setup complete! Starting application...")
            print()
            self.run_application()
            
        except KeyboardInterrupt:
            print("\n🛑 Setup interrupted by user")
        except Exception as e:
            self.print_error(f"Setup failed: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hyperliquid Position Monitor Startup Script")
    parser.add_argument(
        "--activate-only", 
        action="store_true", 
        help="Only activate virtual environment without running the application"
    )
    parser.add_argument(
        "--shell", 
        action="store_true", 
        help="Start an interactive shell with virtual environment activated"
    )
    
    args = parser.parse_args()
    
    starter = HyperliquidStarter()
    
    if args.activate_only or args.shell:
        # Setup environment without running the application
        starter.print_header()
        starter.check_python_version()
        starter.create_venv()
        starter.upgrade_pip()
        starter.install_requirements()
        
        if args.shell:
            starter.start_interactive_shell()
        else:
            starter.print_activation_instructions()
    else:
        starter.run()


if __name__ == "__main__":
    main()
