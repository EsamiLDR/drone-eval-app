from setuptools import setup, find_packages

setup(
    name="drone-eval-app",
    version="6.0",
    description="This is a drone evaluation application that provides related functions and services.",  # 添加描述信息
    long_description="This is a more detailed description of the drone evaluation application. It can be used to evaluate drones, and it depends on some specific Python libraries.",  # 可选，详细描述
    long_description_content_type="text/markdown",  # 可选，指定详细描述的格式
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
            "drone-eval=src.fqapp:main",  
        ],
    },
)
