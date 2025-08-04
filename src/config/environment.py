"""
Environment configuration validation and setup.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from rich.console import Console
from dotenv import load_dotenv

console = Console()


class EnvironmentConfig:
    """Environment configuration validator and manager."""
    
    def __init__(self):
        self.required_vars = [
            'HL_WALLET_ADDRESS',
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID'
        ]
        
        self.optional_vars = {
            'REFRESH_INTERVAL_SECONDS': '300',
            'PRICE_SYMBOLS': 'BTC,ETH,SOL',
            'API_TIMEOUT': '30',
            'CACHE_DURATION': '30',
            'LOG_LEVEL': 'INFO',
            'LOG_DIRECTORY': 'logs'
        }
        
        # Load environment variables from .env file
        self.load_environment()
    
    def load_environment(self) -> bool:
        """Load environment variables from .env file."""
        env_file = Path(".env")
        
        if env_file.exists():
            load_dotenv(env_file)
            console.print("📄 [bold green]Environment variables loaded from .env file[/bold green]")
            return True
        else:
            console.print("⚠️ [bold yellow].env file not found, using system environment variables[/bold yellow]")
            return False
    
    def validate_environment(self) -> bool:
        """Validate all required environment variables are set."""
        missing_vars = []
        
        for var in self.required_vars:
            value = os.getenv(var)
            if not value or value.startswith('your_'):
                missing_vars.append(var)
        
        if missing_vars:
            console.print("❌ [bold red]Missing or incomplete environment variables:[/bold red]")
            for var in missing_vars:
                console.print(f"  • {var}")
            console.print("\n📝 Please update your .env file with actual values")
            return False
        
        console.print("✅ [bold green]Environment variables validated successfully[/bold green]")
        return True
    
    def check_env_file(self) -> bool:
        """Check if .env file exists and is properly configured."""
        env_file = Path(".env")
        
        if not env_file.exists():
            console.print("❌ [bold red].env file not found[/bold red]")
            console.print("📝 Please create .env file using .env.example as template")
            return False
        
        try:
            with open(env_file, 'r') as f:
                content = f.read()
            
            # Check for placeholder values
            placeholder_patterns = ['your_', 'YOUR_', 'example_', 'EXAMPLE_']
            
            for var in self.required_vars:
                if f"{var}=" not in content:
                    console.print(f"❌ [bold red]Missing {var} in .env file[/bold red]")
                    return False
                
                # Check for placeholder values
                for pattern in placeholder_patterns:
                    if f"{var}={pattern}" in content:
                        console.print(f"❌ [bold red]{var} contains placeholder value[/bold red]")
                        return False
            
            console.print("✅ [bold green].env file validated successfully[/bold green]")
            return True
            
        except Exception as e:
            console.print(f"❌ [bold red]Error reading .env file: {e}[/bold red]")
            return False
    
    def setup_directories(self) -> None:
        """Create necessary directories."""
        log_dir = Path(os.getenv('LOG_DIRECTORY', 'logs'))
        log_dir.mkdir(exist_ok=True)
        console.print(f"📁 Log directory ready: {log_dir}")
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get current environment information."""
        return {
            'python_version': sys.version,
            'platform': sys.platform,
            'working_directory': os.getcwd(),
            'env_file_exists': Path('.env').exists(),
            'log_directory': os.getenv('LOG_DIRECTORY', 'logs'),
            'configured_symbols': os.getenv('PRICE_SYMBOLS', 'BTC,ETH,SOL').split(',')
        }
    
    def print_environment_summary(self) -> None:
        """Print environment configuration summary."""
        info = self.get_environment_info()
        
        console.print("\n📊 [bold blue]Environment Summary[/bold blue]")
        console.print(f"• Python Version: {info['python_version'].split()[0]}")
        console.print(f"• Platform: {info['platform']}")
        console.print(f"• Working Directory: {info['working_directory']}")
        console.print(f"• Environment File: {'✅ Found' if info['env_file_exists'] else '❌ Missing'}")
        console.print(f"• Log Directory: {info['log_directory']}")
        console.print(f"• Price Symbols: {', '.join(info['configured_symbols'])}")
    
    def validate_all(self) -> bool:
        """Validate entire environment setup."""
        console.print("🔍 [bold cyan]Validating Environment Configuration[/bold cyan]")
        
        # Check .env file
        if not self.check_env_file():
            return False
        
        # Validate environment variables
        if not self.validate_environment():
            return False
        
        # Setup directories
        self.setup_directories()
        
        # Print summary
        self.print_environment_summary()
        
        return True
