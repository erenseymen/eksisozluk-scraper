#!/usr/bin/env python3
"""Setup script for eksisozluk-scraper"""

from setuptools import setup
from setuptools.command.install import install
from pathlib import Path
import os
import shutil
import subprocess
import sys

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


class InstallWithCompletions(install):
    """Custom install command that also installs shell completions"""
    
    def run(self):
        # Run the standard install
        install.run(self)
        
        # Install completions
        self.install_completions()
    
    def install_completions(self):
        """Install shell completions for the CLI"""
        # Check if we're in a pipx environment
        is_pipx = "PIPX_HOME" in os.environ or "pipx" in str(Path(sys.executable).parent).lower()
        
        # Get the installation prefix
        if self.prefix:
            prefix = Path(self.prefix)
        else:
            prefix = Path(sys.prefix)
        
        completions_dir = Path(__file__).parent / "completions"
        
        # Install fish completion
        fish_completion_source = completions_dir / "eksisozluk-scraper.fish"
        if fish_completion_source.exists():
            # For user installs (pip install --user) or pipx, use ~/.local/share/fish/vendor_completions.d
            # For system installs, use the system fish completions directory
            if self.user or is_pipx:
                fish_dir = Path.home() / ".local" / "share" / "fish" / "vendor_completions.d"
            else:
                fish_dir = prefix / "share" / "fish" / "vendor_completions.d"
            
            fish_dir.mkdir(parents=True, exist_ok=True)
            fish_dest = fish_dir / "eksisozluk-scraper.fish"
            try:
                shutil.copy2(fish_completion_source, fish_dest)
                print(f"Installed fish completion to {fish_dest}")
            except Exception as e:
                print(f"Warning: Could not install fish completion: {e}", file=sys.stderr)
        
        # Install zsh completion
        zsh_completion_source = completions_dir / "_eksisozluk-scraper"
        if zsh_completion_source.exists():
            # For user installs or pipx, use ~/.local/share/zsh/site-functions
            # For system installs, use the system zsh site-functions directory
            if self.user or is_pipx:
                zsh_dir = Path.home() / ".local" / "share" / "zsh" / "site-functions"
            else:
                zsh_dir = prefix / "share" / "zsh" / "site-functions"
            
            zsh_dir.mkdir(parents=True, exist_ok=True)
            zsh_dest = zsh_dir / "_eksisozluk-scraper"
            try:
                shutil.copy2(zsh_completion_source, zsh_dest)
                print(f"Installed zsh completion to {zsh_dest}")
            except Exception as e:
                print(f"Warning: Could not install zsh completion: {e}", file=sys.stderr)
        
        # Install bash completion using argcomplete
        # For pipx, we need to find register-python-argcomplete in the pipx environment
        register_cmd = "register-python-argcomplete"
        if is_pipx:
            # Try to find register-python-argcomplete in the pipx environment
            # pipx installs binaries in the same directory as the Python executable
            pipx_bin = Path(sys.executable).parent / register_cmd
            if pipx_bin.exists():
                register_cmd = str(pipx_bin)
            else:
                # Try in the bin directory of the pipx environment
                pipx_env_bin = Path(sys.executable).parent.parent / "bin" / register_cmd
                if pipx_env_bin.exists():
                    register_cmd = str(pipx_env_bin)
                else:
                    # Try to find it using shutil.which in the pipx environment
                    # or check if we can import and use argcomplete directly
                    try:
                        # Try to find the script in the PATH relative to the executable
                        which_result = shutil.which(register_cmd, path=str(Path(sys.executable).parent))
                        if which_result:
                            register_cmd = which_result
                    except Exception:
                        pass
        
        try:
            # Try to use register-python-argcomplete if available
            result = subprocess.run(
                [register_cmd, "eksisozluk-scraper"],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0 and result.stdout:
                # For user installs or pipx, use ~/.local/share/bash-completion/completions
                # For system installs, try system locations
                if self.user or is_pipx:
                    bash_dir = Path.home() / ".local" / "share" / "bash-completion" / "completions"
                else:
                    # Try common system locations
                    for sys_path in [
                        prefix / "share" / "bash-completion" / "completions",
                        Path("/usr/share/bash-completion/completions"),
                        Path("/etc/bash_completion.d"),
                    ]:
                        if sys_path.exists() or prefix == Path(sys.prefix):
                            bash_dir = sys_path
                            break
                    else:
                        bash_dir = prefix / "share" / "bash-completion" / "completions"
                
                bash_dir.mkdir(parents=True, exist_ok=True)
                bash_dest = bash_dir / "eksisozluk-scraper"
                try:
                    bash_dest.write_text(result.stdout)
                    print(f"Installed bash completion to {bash_dest}")
                    if is_pipx:
                        print("Note: For pipx installations, you may need to restart your shell or run:")
                        print("  eval \"$(register-python-argcomplete eksisozluk-scraper)\"")
                except Exception as e:
                    print(f"Warning: Could not install bash completion: {e}", file=sys.stderr)
            elif is_pipx:
                print("Note: Bash completion not automatically installed for pipx.")
                print("To enable it, add this to your ~/.bashrc or ~/.zshrc:")
                print("  eval \"$(register-python-argcomplete eksisozluk-scraper)\"")
        except FileNotFoundError:
            # register-python-argcomplete not found
            if not is_pipx:
                print("Warning: register-python-argcomplete not found. Bash completion not installed.")
                print("Install argcomplete to enable bash completion: pip install argcomplete")
            else:
                print("Note: For pipx installations, to enable bash completion, add this to your ~/.bashrc or ~/.zshrc:")
                print("  eval \"$(register-python-argcomplete eksisozluk-scraper)\"")
        except Exception as e:
            print(f"Warning: Could not generate bash completion: {e}", file=sys.stderr)


setup(
    name="eksisozluk-scraper",
    version="2.1.1",
    description="Ekşi Sözlük Scraper - AI-friendly output üreten terminal tabanlı scraper",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Eren Seymen",
    author_email="",
    url="https://github.com/erenseymen/eksisozluk-scraper",
    py_modules=["eksisozluk_scraper"],
    python_requires=">=3.8",
    # Dependencies are defined in pyproject.toml [project] dependencies
    # install_requires is omitted to let setuptools read from pyproject.toml
    entry_points={
        "console_scripts": [
            "eksisozluk-scraper=eksisozluk_scraper:main",
        ],
    },
    cmdclass={
        "install": InstallWithCompletions,
    },
    license="GPL-3.0-or-later",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)

