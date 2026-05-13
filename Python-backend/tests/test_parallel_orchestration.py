"""
并行编排模式测试脚本

测试并行编排和批量编排的性能对比
"""
import time
import asyncio
from typing import Dict, Any, List


def simulate_llm_call(module_id: int, duration: float = 2.0) -> Dict[str, Any]:
    """模拟 LLM 调用"""
    print(f"  [模块{module_id}] 开始生成...")
    time.sleep(duration)
    print(f"  [模块{module_id}] 生成完成!")
    return {
        "module_id": module_id,
        "title": f"模块 {module_id}",
        "content": f"这是模块 {module_id} 的内容",
        "duration": duration,
    }


def batch_orchestration(num_modules: int = 5) -> Dict[str, Any]:
    """批量编排模式：一次性生成所有模块"""
    print("\n" + "="*60)
    print("批量编排模式")
    print("="*60)
    
    start_time = time.time()
    
    # 模拟一次性调用 LLM 生成所有模块
    print("  [批量] 开始生成所有模块...")
    time.sleep(8.0)  # 模拟 8 秒的 LLM 调用
    print("  [批量] 所有模块生成完成!")
    
    modules = [
        {
            "module_id": i + 1,
            "title": f"模块 {i + 1}",
            "content": f"这是模块 {i + 1} 的内容",
        }
        for i in range(num_modules)
    ]
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n总耗时: {duration:.2f} 秒")
    print(f"模块数量: {len(modules)}")
    print(f"平均每模块: {duration / len(modules):.2f} 秒")
    
    return {
        "mode": "batch",
        "modules": modules,
        "duration": duration,
        "num_modules": num_modules,
    }


async def parallel_orchestration(num_modules: int = 5) -> Dict[str, Any]:
    """并行编排模式：为每个模块并发生成内容"""
    print("\n" + "="*60)
    print("并行编排模式")
    print("="*60)
    
    start_time = time.time()
    
    loop = asyncio.get_event_loop()
    
    # 为每个模块创建并发任务
    tasks = []
    for i in range(num_modules):
        task = loop.run_in_executor(
            None,
            simulate_llm_call,
            i + 1,
            2.0,  # 每个模块生成耗时 2 秒
        )
        tasks.append(task)
    
    # 并发执行所有任务
    print(f"  [并行] 同时启动 {num_modules} 个生成任务...")
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理结果
    modules = []
    for result in results:
        if isinstance(result, Exception):
            print(f"  [错误] 模块生成失败: {str(result)}")
        else:
            modules.append(result)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"\n总耗时: {duration:.2f} 秒")
    print(f"模块数量: {len(modules)}")
    print(f"平均每模块: {duration / len(modules):.2f} 秒")
    
    return {
        "mode": "parallel",
        "modules": modules,
        "duration": duration,
        "num_modules": num_modules,
    }


def compare_modes(num_modules: int = 5):
    """对比两种模式的性能"""
    print("\n" + "#"*60)
    print(f"# 性能对比测试 - {num_modules} 个模块")
    print("#"*60)
    
    # 测试批量模式
    batch_result = batch_orchestration(num_modules)
    
    # 测试并行模式
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    parallel_result = loop.run_until_complete(parallel_orchestration(num_modules))
    loop.close()
    
    # 对比结果
    print("\n" + "="*60)
    print("性能对比结果")
    print("="*60)
    
    print(f"\n批量模式:")
    print(f"  总耗时: {batch_result['duration']:.2f} 秒")
    print(f"  模块数量: {batch_result['num_modules']}")
    
    print(f"\n并行模式:")
    print(f"  总耗时: {parallel_result['duration']:.2f} 秒")
    print(f"  模块数量: {parallel_result['num_modules']}")
    
    # 计算提升
    time_saved = batch_result['duration'] - parallel_result['duration']
    improvement = (time_saved / batch_result['duration']) * 100
    
    print(f"\n性能提升:")
    print(f"  节省时间: {time_saved:.2f} 秒")
    print(f"  提升比例: {improvement:.1f}%")
    
    if improvement > 0:
        print(f"  ✅ 并行模式更快!")
    elif improvement < 0:
        print(f"  ⚠️ 批量模式更快!")
    else:
        print(f"  ➡️ 两种模式性能相同")


if __name__ == "__main__":
    # 测试不同数量的模块
    for num in [3, 5, 8]:
        compare_modes(num)
        print("\n" + "="*60 + "\n")
