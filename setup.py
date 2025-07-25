from setuptools import setup, find_packages

setup(
    name="ocr_translator",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.19.0",
        "opencv-python>=4.5.0",
        "pytesseract>=0.3.8",
        "Pillow>=8.0.0",
        "pyautogui>=0.9.53",
    ],
    extras_require={
        "google": ["google-cloud-translate>=3.0.0"],
        "deepl": ["deepl>=1.12.0"],
        "marianmt": ["transformers>=4.18.0", "torch>=1.10.0", "sentencepiece>=0.1.96"],
        "keyboard": ["keyboard>=0.13.5"],
        "gpu": ["nvidia-ml-py3>=7.352.0"],
        "all": [
            "google-cloud-translate>=3.0.0",
            "deepl>=1.12.0",
            "transformers>=4.18.0", 
            "torch>=1.10.0", 
            "sentencepiece>=0.1.96",
            "keyboard>=0.13.5",
            "nvidia-ml-py3>=7.352.0",
        ],
    },
    python_requires=">=3.7",
    include_package_data=True,
    package_data={
        "ocr_translator": ["*.csv"],
    },
    entry_points={
        "console_scripts": [
            "ocr_translator=ocr_translator.main:main_entry_point",
        ],
    },
    author="Tomasz Kamiński",
    description="Real-time screen OCR and translation tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="ocr, translation, screen-capture, real-time",
    url="https://github.com/yourusername/ocr-translator",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Utilities",
        "Topic :: Desktop Environment",
        "Topic :: Text Processing :: Linguistic",
    ],
)
