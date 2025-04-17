from setuptools import setup, find_packages

setup(
    name="drone-eval-app",
    version="6.0",
    packages=find_packages(),
    install_requires=[
        "tkinter",          # 通常系统自带
        "pyyaml>=6.0",
        "openai>=1.0",
    ],
    data_files=[
        ("share/drone-eval-app", ["src/newprompts.yaml", "src/pic1.png"]),
    ],
    entry_points={
        "console_scripts": [
            "drone-eval=src.fqapp6点0:main",  
        ],
    },
)