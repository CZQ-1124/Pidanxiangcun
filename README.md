# 皮蛋乡村（Pidan System）
1、项目结构：
皮蛋乡村第六版/
├── .streamlit/
├── config/ # 配置文件目录
├── data/ # 数据目录
├── images/ # 云平台示例图片
├── modules/ # 系统核心功能模块代码
├── prompts/ # 调用大模型提示词模板目录
├── services/ # 服务目录，存放模型调用、接口请求等
├── venv/ 
├── .env.example 
├── .gitignore 
├── app.py 
├── README.md 
└── requirements.txt  

2、本地部署方式：vs code（streamlit）。

3、运行方式（代码如下：）
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
