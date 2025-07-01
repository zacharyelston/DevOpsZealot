from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="devops-zealot",
    version="0.1.0",
    author="Zachary Elston",
    author_email="zacharyelston@gmail.com",
    description="Autonomous AI-powered infrastructure editing tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/zacharyelston/DevOpsZealot",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.11",
    install_requires=[
        "docker>=6.1.3",
        "gitpython>=3.1.40",
        "openai>=1.12.0",
        "redis>=5.0.1",
        "pydantic>=2.5.0",
        "fastapi>=0.109.0",
        "uvicorn>=0.27.0",
    ],
    entry_points={
        "console_scripts": [
            "zealot=zealot.cli:main",
            "zealot-server=zealot.server:main",
        ],
    },
)
