from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path)

class MyModel:
    _model = None

    @staticmethod
    def get_model():
        if MyModel._model is None:
            MyModel._model = ChatOpenAI(
                model=os.getenv("MODEL_NAME"),
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_api_base=os.getenv("OPENAI_API_BASE"),
                max_tokens=2048,
                temperature=0.3
            )
        return MyModel._model

# # 类外部调用
# if __name__ == "__main__":
#     m = MyModel.get_model()
#     # 正确调用invoke方法
#     rs = m.invoke("hi")
#     #print(rs.content)