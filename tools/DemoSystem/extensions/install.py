#!/usr/bin/env python3
import yaml
import json
import os
import glob
import shutil
from pathlib import Path


def escape_html(text):
    """转义HTML特殊字符"""
    if not text:
        return ""
    return (str(text).replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#039;'))


def build_html_from_description(description):
    """根据描述类型构建HTML"""
    if not description:
        return ""

    html_parts = []

    for item in description:
        item_type = item.get('type', 'paragraph')
        content = item.get('content', '')

        if item_type == 'paragraph':
            # 处理段落
            html_parts.append(f'<div>{escape_html(content)}</div>')

        elif item_type == 'code_block':
            # 处理代码块
            title = item.get('title', '')
            code_content = content.strip()

            code_html = f'''<div class="code-block">
    <div class="code-header">
        <span class="code-title">{escape_html(title)}</span>
    </div>
    <pre class="code-content">{escape_html(code_content)}</pre>
</div>'''
            html_parts.append(code_html)

        elif item_type == 'note':
            # 处理注意事项
            html_parts.append(f'<div class="note">{escape_html(content)}</div>')

        elif item_type == 'warning':
            # 处理警告
            html_parts.append(f'<div class="warning">{escape_html(content)}</div>')

    return '\n'.join(html_parts)


def build_inner_html(step):
    """根据步骤类型构建innerHtml"""
    step_type = step.get('type', 'description_with_command')

    if step_type == 'command_only':
        # 只有命令的步骤
        if 'description' in step:
            return build_html_from_description(step['description'])
        return ''

    elif step_type == 'description_with_command':
        # 描述后跟命令
        if 'description' in step:
            return build_html_from_description(step['description'])
        return ''

    elif step_type == 'description_with_command_group':
        # 描述后跟命令组
        if 'description' in step:
            return build_html_from_description(step['description'])
        return ''

    elif step_type == 'simple_description':
        # 简单描述
        if 'description' in step:
            return build_html_from_description(step['description'])
        return ''

    return ''


def process_cmd_groups(cmd_groups):
    """处理命令组，生成cmdGroupKwargs"""
    cmd_group_kwargs = []

    for group in cmd_groups:
        group_config = {
            'title': group.get('title', ''),
            'tooltip': group.get('tooltip', ''),
            'cmdKwargs': []
        }

        # 处理组内的每个命令
        for cmd in group.get('commands', []):
            cmd_kwargs = {k: v for k, v in cmd.items()}
            group_config['cmdKwargs'].append(cmd_kwargs)

        cmd_group_kwargs.append(group_config)

    return cmd_group_kwargs


def generate_ts_from_yaml(yaml_file, output_ts_file):
    """
    从YAML配置文件生成TypeScript配置文件
    """
    try:
        # 读取YAML文件
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except Exception as e:
        print(f"  错误: 无法读取YAML文件 {yaml_file}: {e}")
        return None

    # 构建配置数组
    ts_config = []

    for section in config_data.get('sections', []):
        section_config = {
            'headerTitle': section.get('headerTitle', ''),
            'text': []
        }

        # 处理每个步骤
        for step in section.get('steps', []):
            step_type = step.get('type', 'description_with_command')

            # 基础配置
            step_config = {}

            # 设置shortText
            if 'shortText' in step:
                step_config['shortText'] = step['shortText']
            else:
                step_config['shortText'] = None

            # 构建innerHtml
            inner_html = build_inner_html(step)
            if inner_html:
                step_config['innerHtml'] = inner_html

            # 处理命令组类型
            if step_type == 'description_with_command_group' and 'cmdGroups' in step:
                # 处理命令组
                step_config['cmdGroupKwargs'] = process_cmd_groups(step['cmdGroups'])

            # 处理普通命令类型
            elif 'commands' in step:
                step_config['cmdKwargs'] = []
                for cmd in step['commands']:
                    cmd_kwargs = {k: v for k, v in cmd.items()}
                    step_config['cmdKwargs'].append(cmd_kwargs)

            # 处理单个命令类型
            elif 'action' in step:
                # 如果没有commands但有action，直接使用step作为cmdKwargs
                step_config['cmdKwargs'] = [{k: v for k, v in step.items()}]

            section_config['text'].append(step_config)

        ts_config.append(section_config)

    # 获取baseInfo
    base_info = config_data.get('baseInfo', {})

    # 生成TypeScript代码
    # 使用自定义的JSON编码器确保中文字符正确处理
    class CustomJSONEncoder(json.JSONEncoder):
        def encode(self, obj):
            # 使用ensure_ascii=False保持中文字符
            return json.dumps(obj, ensure_ascii=False, indent=2)

    # 生成包含baseInfo和config的TypeScript代码
    ts_code = """export const baseInfo = {}

export const config = {}

export default config
""".format(CustomJSONEncoder().encode(base_info),
           CustomJSONEncoder().encode(ts_config))

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_ts_file), exist_ok=True)

    # 写入TypeScript文件
    with open(output_ts_file, 'w', encoding='utf-8') as f:
        f.write(ts_code)

    return ts_config, base_info


def validate_yaml_structure(yaml_file):
    """验证YAML文件结构"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
    except Exception as e:
        print(f"  错误: 无法读取YAML文件 {yaml_file}: {e}")
        return False

    required_fields = ['baseInfo', 'sections']
    for field in required_fields:
        if field not in config_data:
            print(f"  错误: YAML文件缺少必要字段: {field}")
            return False

    return True


def find_all_yml_files(base_dir):
    """查找所有YAML文件"""
    yml_files = []

    # 使用glob递归查找所有.yml文件
    for yml_file in glob.glob(os.path.join(base_dir, '**', '*.yml'), recursive=True):
        # 确保文件路径是相对于base_dir的
        rel_path = os.path.relpath(yml_file, base_dir)
        yml_files.append((yml_file, rel_path))

    return yml_files


def copy_assets(source_base_dir, target_base_dir, menus_data):
    """复制资源文件（图片、视频等）"""
    assets_copied = {
        'img': [],
        'video': []
    }

    def process_menu_item(item):
        # 复制图片
        if 'meta' in item and 'img' in item['meta'] and item['meta']['img']:
            img_path = item['meta']['img']
            if img_path:  # 非空字符串
                # 构建源文件路径
                source_img = os.path.join(source_base_dir, img_path)
                # 构建目标文件路径 - 修正：直接使用assets_target_dir
                target_img = os.path.join(
                    os.path.join(target_base_dir, 'img'), os.path.basename(os.path.basename(img_path))
                )

                # 确保目标目录存在
                os.makedirs(os.path.dirname(target_img), exist_ok=True)

                # 复制文件
                if os.path.exists(source_img):
                    shutil.copy2(source_img, target_img)
                    assets_copied['img'].append(img_path)
                    print(f"    复制图片: {img_path}")
                    print(f"      源路径: {source_img}")
                    print(f"      目标路径: {target_img}")
                else:
                    print(f"    ⚠️ 图片不存在: {source_img}")

        # 复制视频
        if 'meta' in item and 'video' in item['meta'] and 'src' in item['meta']['video']:
            video_src = item['meta']['video']['src']
            if video_src:  # 非空字符串
                # 构建源文件路径
                source_video = os.path.join(source_base_dir, video_src)
                target_video = os.path.join(
                    os.path.join(target_base_dir, 'video'), os.path.basename(os.path.basename(video_src))
                )

                # 确保目标目录存在
                os.makedirs(os.path.dirname(target_video), exist_ok=True)

                # 复制文件
                if os.path.exists(source_video):
                    shutil.copy2(source_video, target_video)
                    assets_copied['video'].append(video_src)
                    print(f"    复制视频: {video_src}")
                    print(f"      源路径: {source_video}")
                    print(f"      目标路径: {target_video}")
                else:
                    print(f"    ⚠️ 视频不存在: {source_video}")

        # 处理子菜单
        if 'children' in item:
            for child in item['children']:
                process_menu_item(child)

    # 处理所有菜单项
    for menu in menus_data:
        process_menu_item(menu)

    return assets_copied


def convert_menus_for_json(menus_data):
    """转换menus数据，准备生成JSON"""

    def convert_item(item):
        # 创建新对象的副本
        new_item = item.copy()

        if 'meta' in new_item:
            new_item['meta'] = new_item['meta'].copy()

            # 处理图片路径 - 使用占位符
            if 'img' in new_item['meta'] and new_item['meta']['img']:
                img_path = new_item['meta']['img']
                if img_path and img_path.strip():
                    # 使用特殊占位符，后续会替换
                    new_item['meta']['img'] = f'__IMG_PLACEHOLDER__{img_path}__'

            # 处理视频路径
            if 'video' in new_item['meta'] and new_item['meta']['video']:
                new_item['meta']['video'] = new_item['meta']['video'].copy()
                video_src = new_item['meta']['video'].get('src', '')
                if video_src and video_src.strip():
                    # 使用特殊占位符
                    new_item['meta']['video']['src'] = f'__VIDEO_PLACEHOLDER__{video_src}__'

        # 递归处理子菜单
        if 'children' in new_item:
            new_item['children'] = [convert_item(child) for child in new_item['children']]

        return new_item

    return [convert_item(menu) for menu in menus_data]


def replace_placeholders_with_new_url(json_str):
    """将JSON字符串中的占位符替换为new URL()表达式"""

    import re

    # 替换img占位符
    def replace_img_placeholder(match):
        path = match.group(1)
        # 确保路径以 @/ 开头
        if not path.startswith('@/'):
            path = '@/{}'.format(path)
        return 'new URL(\'{}\', import.meta.url).href'.format(path)

    # 替换video.src占位符
    def replace_video_placeholder(match):
        path = match.group(1)
        # 确保路径以 @/ 开头
        if not path.startswith('@/'):
            path = '@/{}'.format(path)
        return 'new URL(\'{}\', import.meta.url).href'.format(path)

    # 先替换video.src占位符
    json_str = re.sub(r'"__VIDEO_PLACEHOLDER__([^"]+)__"', replace_video_placeholder, json_str)

    # 再替换img占位符
    json_str = re.sub(r'"__IMG_PLACEHOLDER__([^"]+)__"', replace_img_placeholder, json_str)

    return json_str


def generate_extensions_index(component_record, menus_data, output_file, target_base_dir):
    """生成扩展的概览index.ts文件，包含componentRecord和menus"""

    # 转换menus数据，使用占位符
    converted_menus = convert_menus_for_json(menus_data)

    # 生成TypeScript代码
    entries = []
    for key, value in component_record.items():
        entries.append('    {}: \'{}\''.format(key, value))

    # 生成menus的JSON字符串
    menus_json = json.dumps(converted_menus, ensure_ascii=False, indent=2)

    # 将占位符替换为new URL()表达式
    menus_ts_code = replace_placeholders_with_new_url(menus_json)

    # 生成完整的TypeScript代码
    ts_code = """export const componentRecord = {{
{entries}
}}

export const menus = {menus}
""".format(entries=',\n'.join(entries), menus=menus_ts_code)

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # 写入TypeScript文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(ts_code)

    print(f"\n已生成扩展概览文件: {output_file}")


def load_menus_config(menus_file):
    """加载menus.yml配置文件"""
    try:
        with open(menus_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        if 'menus' not in config_data:
            print(f"  警告: menus.yml文件缺少menus字段")
            return []

        return config_data['menus']

    except Exception as e:
        print(f"  错误: 无法读取menus.yml文件 {menus_file}: {e}")
        return []


def main():
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 输出目录（frontend/src/extensions/）
    output_base_dir = os.path.join(os.path.dirname(script_dir), 'frontend', 'src', 'extensions')

    # 前端资源目录（frontend/src/assets/）
    assets_target_dir = os.path.join(os.path.dirname(script_dir), 'frontend', 'src', 'assets')

    print(f"脚本目录: {script_dir}")
    print(f"输出目录: {output_base_dir}")
    print(f"资源目录: {assets_target_dir}")

    # 查找所有YAML文件
    yml_files = find_all_yml_files(script_dir)

    if not yml_files:
        print("未找到任何YML文件")
        return

    print(f"找到 {len(yml_files)} 个YML文件:")

    component_record = {}
    successful_count = 0

    # 先处理所有实验配置文件
    for yml_file, rel_path in yml_files:
        # 跳过menus.yml文件，单独处理
        if os.path.basename(yml_file) == 'menus.yml':
            continue

        print(f"\n处理实验文件: {rel_path}")

        # 验证YAML结构
        if not validate_yaml_structure(yml_file):
            print(f"  ⚠️ 跳过: {rel_path} (结构验证失败)")
            continue

        # 生成组件名称（使用文件名，去掉扩展名）
        component_name = os.path.splitext(os.path.basename(yml_file))[0]

        # 生成输出路径
        # 保持目录结构，但将.yml替换为/index.ts
        rel_dir = os.path.dirname(rel_path)
        output_dir = os.path.join(output_base_dir, rel_dir, component_name)
        output_ts_file = os.path.join(output_dir, 'index.ts')

        print(f"  组件名称: {component_name}")
        print(f"  输出文件: {output_ts_file}")

        # 生成TypeScript配置文件
        result = generate_ts_from_yaml(yml_file, output_ts_file)

        if result:
            config, base_info = result

            # 添加到组件记录
            # 相对路径使用正斜杠（符合TypeScript/前端习惯）
            component_key = component_name
            if rel_dir:
                component_path = f"{rel_dir.replace(os.sep, '/')}/{component_name}"
            else:
                component_path = component_name
            component_record[component_key] = component_path

            # 统计信息
            total_steps = sum(len(section['text']) for section in config)
            print(f"  ✅ 成功生成: {len(config)} 个部分, {total_steps} 个步骤")
            print(f"  🔹 baseInfo: {base_info.get('name', '未命名')}")
            successful_count += 1
        else:
            print(f"  ❌ 失败: {rel_path}")

    # 处理menus.yml文件
    menus_file = os.path.join(script_dir, 'menus.yml')
    menus_data = []

    if os.path.exists(menus_file):
        print(f"\n处理菜单文件: menus.yml")
        menus_data = load_menus_config(menus_file)
        if menus_data:
            print(f"  ✅ 成功加载: {len(menus_data)} 个菜单项")

            # 统计子菜单项
            child_count = sum(len(menu.get('children', [])) for menu in menus_data)
            print(f"    包含: {child_count} 个子菜单项")

            # 复制资源文件
            print(f"\n复制资源文件:")
            assets_copied = copy_assets(script_dir, assets_target_dir, menus_data)

            print(f"    图片: {len(assets_copied['img'])} 个")
            print(f"    视频: {len(assets_copied['video'])} 个")
    else:
        print(f"\n⚠️ 未找到menus.yml文件，将只生成componentRecord")

    # 生成扩展的概览index.ts文件（包含componentRecord和menus）
    overview_file = os.path.join(output_base_dir, 'index.ts')
    generate_extensions_index(component_record, menus_data, overview_file, assets_target_dir)

    # 打印总结
    print(f"\n{'=' * 50}")
    print(f"处理完成:")
    print(f"  总共找到: {len(yml_files)} 个YML文件")
    print(f"  成功生成: {successful_count} 个实验组件")
    print(f"  加载菜单: {len(menus_data)} 个主菜单项")
    print(f"  失败: {len(yml_files) - successful_count - (1 if os.path.exists(menus_file) else 0)} 个")

    if component_record:
        print(f"\n生成的实验组件:")
        for key, value in sorted(component_record.items()):
            print(f"  {key}: '{value}'")


if __name__ == "__main__":
    main()
