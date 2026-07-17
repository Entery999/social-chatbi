from pydantic import BaseModel, Field

class TableResponse(BaseModel):
    column_names: list = Field(...,description="英文表头")
    data: list[dict[str,str]] = Field(...,description="数据")

class AnalyzeResponse(BaseModel):
    table: TableResponse = Field(...,description="表格数据")
    result: str = Field(...,description="分析结果")
    json: str = Field(...,description="图表分析")

