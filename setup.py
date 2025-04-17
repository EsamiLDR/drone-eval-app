from setuptools import setup, find_packages

setup(
    name="drone-eval-app",
    version="6.0",
    description="Drone evaluation application",
    long_description=open("README.md").read(),  # 确保有 README.md 文件
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),  # 明确指定包目录
    package_dir={"": "src"},             # 关键：声明包根目录为 src
    install_requires=[
        "tkinter",
        "pyyaml>=6.0",
        "openai>=1.0",
    ],
    package_data={
        "drone_eval_app": ["*.yaml", "*.png"],  # 使用 package_data 替代 data_files
    },
    entry_points={
        "console_scripts": [
            "drone-eval=src.fqapp:main",  # 确保路径正确
        ],
    },
    python_requires=">=3.10",  # 明确 Python 版本要求
)
