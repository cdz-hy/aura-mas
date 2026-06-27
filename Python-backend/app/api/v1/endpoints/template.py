"""
模板管理 API — 列出、查看详情、上传新模板
"""
import logging
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app.agents.pptx_template_engine import list_templates, get_template_engine, TEMPLATES_DIR

logger = logging.getLogger("api.template")
router = APIRouter()


@router.get("/templates")
async def get_templates():
    """列出所有可用模板"""
    templates = list_templates()
    return {"templates": templates}


@router.get("/templates/{name}")
async def get_template_detail(name: str):
    """获取模板详情（布局列表、描述、幻灯片数）"""
    template_dir = TEMPLATES_DIR / name
    if not template_dir.exists():
        raise HTTPException(status_code=404, detail=f"模板 '{name}' 不存在")

    try:
        engine = get_template_engine(name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载模板失败: {e}")

    desc_file = template_dir / "description.txt"
    description = desc_file.read_text(encoding="utf-8").strip() if desc_file.exists() else ""

    return {
        "name": name,
        "description": description,
        "slide_count": len(engine.prs.slides),
        "layouts": [
            {
                "name": layout_name,
                "template_id": info["template_id"],
                "slide_count": len(info.get("slides", [])),
                "elements": [
                    {"name": e["name"], "type": e["type"]}
                    for e in info.get("elements", [])
                ],
            }
            for layout_name, info in engine.layouts.items()
        ],
        "functional_keys": engine.functional_keys,
    }


@router.post("/templates/upload")
async def upload_template(
    file: UploadFile = File(..., description="PPTX 模板文件"),
    name: str = Form(..., description="模板名称（英文，用作目录名）"),
    description: str = Form("", description="模板描述"),
):
    """上传新 PPTX 模板并自动归纳布局"""
    if not file.filename.endswith(".pptx"):
        raise HTTPException(status_code=400, detail="仅支持 .pptx 文件")

    # 模板名称校验
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        raise HTTPException(status_code=400, detail="模板名称仅支持英文、数字、下划线、连字符")

    template_dir = TEMPLATES_DIR / name
    if template_dir.exists():
        raise HTTPException(status_code=409, detail=f"模板 '{name}' 已存在")

    try:
        # 1. 保存源文件
        template_dir.mkdir(parents=True, exist_ok=True)
        source_path = template_dir / "source.pptx"
        with open(source_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 2. 运行归纳流水线
        from app.agents.pptx_inductor import induct_template
        induction = induct_template(str(source_path))

        # 3. 保存归纳结果
        import json
        induction_path = template_dir / "slide_induction.json"
        with open(induction_path, "w", encoding="utf-8") as f:
            json.dump(induction, f, ensure_ascii=False, indent=2)

        # 4. 保存描述
        if description:
            desc_path = template_dir / "description.txt"
            desc_path.write_text(description, encoding="utf-8")

        logger.info(f"[模板] 上传成功: {name}, {len(induction) - 2} 个布局")

        return {
            "name": name,
            "description": description,
            "layouts_count": len(induction) - 2,  # 减去 functional_keys 和 language
            "message": "模板上传并归纳成功",
        }

    except HTTPException:
        raise
    except Exception as e:
        # 清理失败的模板目录
        if template_dir.exists():
            shutil.rmtree(template_dir, ignore_errors=True)
        logger.error(f"[模板] 上传失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"模板处理失败: {e}")


@router.delete("/templates/{name}")
async def delete_template(name: str):
    """删除模板"""
    template_dir = TEMPLATES_DIR / name
    if not template_dir.exists():
        raise HTTPException(status_code=404, detail=f"模板 '{name}' 不存在")

    shutil.rmtree(template_dir)
    return {"message": f"模板 '{name}' 已删除"}
