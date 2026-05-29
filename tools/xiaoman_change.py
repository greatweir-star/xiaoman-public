"""
xiaoman-change: 小满形象生成工具

用法:
    python xiaoman_change.py --input 素材图.jpg --output ../web/public/assets/xiaoman/

功能:
    1. 分析素材图特征
    2. 生成全套小满图片:
       - avatar.jpg: 聊天头像
       - onboarding.png: 引导页形象
       - styles/fresh.png: 清新动画风格
       - styles/korean.png: 韩系插画风格
       - styles/watercolor.png: 温柔水彩风格
"""

import argparse
import json
import os
import sys
from pathlib import Path

# 生成质量配置：low(最快/手机够用) / medium / high
QUALITY = "low"

# 提示词模板
PROMPTS = {
    "avatar": {
        "prompt": (
            "Portrait of a cute Chinese middle school girl, based on the reference image. "
            "Soft watercolor illustration style, warm pastel background. "
            "Friendly gentle smile, looking directly at viewer. "
            "Clean simple composition, circular crop suitable for avatar. "
            "High quality, detailed facial features matching reference."
        ),
        "negative": "cartoon, anime, 3d render, ugly, deformed, extra limbs",
    },
    "onboarding": {
        "prompt": (
            "Full body illustration of a cute Chinese middle school girl, based on reference image. "
            "Warm watercolor style, soft pastel tones. "
            "Standing pose, welcoming gesture, gentle smile. "
            "Dreamy background with soft bokeh. "
            "High quality detailed illustration, suitable for app splash screen."
        ),
        "negative": "cartoon, anime, 3d render, ugly, deformed",
    },
    "fresh": {
        "prompt": (
            "Cute Chinese middle school girl portrait, fresh animation style inspired by Makoto Shinkai. "
            "Soft glowing light, detailed background with sky and clouds. "
            "Gentle expression, matching reference image features. "
            "Warm color palette, cinematic lighting."
        ),
        "negative": "realistic photo, ugly, deformed, dark",
    },
    "korean": {
        "prompt": (
            "Fashion illustration of a cute Chinese middle school girl, Korean illustration style. "
            "Clean lines, modern aesthetic, soft colors. "
            "Stylish outfit, confident pose, matching reference features. "
            "Minimalist background, magazine cover quality."
        ),
        "negative": "realistic photo, ugly, deformed, messy",
    },
    "watercolor": {
        "prompt": (
            "Hand-painted watercolor portrait of a cute Chinese middle school girl. "
            "Soft pastel tones, gentle brush strokes, dreamy atmosphere. "
            "Warm yellow and peach background, matching reference features. "
            "Artistic illustration, gallery quality."
        ),
        "negative": "realistic photo, digital art, ugly, deformed",
    },
}


def generate_image(ref_image: str, task: str, output_path: str):
    """调用图像生成API生成单张图片"""
    config = PROMPTS.get(task)
    if not config:
        print(f"Unknown task: {task}")
        return False

    print(f"Generating {task}...")
    print(f"  Prompt: {config['prompt'][:80]}...")

    # 这里可以集成实际的图像生成API
    # 目前输出提示词，由调用方执行生成
    result = {
        "task": task,
        "output": output_path,
        "ref_image": ref_image,
        "prompt": config["prompt"],
        "negative_prompt": config["negative"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return True


def main():
    parser = argparse.ArgumentParser(description="小满形象生成工具")
    parser.add_argument("--input", "-i", required=True, help="素材图路径")
    parser.add_argument("--output", "-o", default="../web/public/assets/xiaoman", help="输出目录")
    parser.add_argument("--task", "-t", choices=list(PROMPTS.keys()), help="单独生成某一项")
    args = parser.parse_args()

    ref_image = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)

    if not os.path.exists(ref_image):
        print(f"Error: Input image not found: {ref_image}")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "styles"), exist_ok=True)

    tasks = {
        "avatar": os.path.join(output_dir, "avatar.jpg"),
        "onboarding": os.path.join(output_dir, "onboarding.png"),
        "fresh": os.path.join(output_dir, "styles", "fresh.png"),
        "korean": os.path.join(output_dir, "styles", "korean.png"),
        "watercolor": os.path.join(output_dir, "styles", "watercolor.png"),
    }

    if args.task:
        # 单独生成一项
        generate_image(ref_image, args.task, tasks[args.task])
    else:
        # 批量生成全套
        print(f"\n🎨 xiaoman-change: 基于 {ref_image} 生成全套图片\n")
        for task, path in tasks.items():
            generate_image(ref_image, task, path)
            print()
        print("✅ 全部生成任务已提交")
        print(f"📁 输出目录: {output_dir}")


if __name__ == "__main__":
    main()
