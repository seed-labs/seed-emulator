#!/usr/bin/env python3
import yaml
import json
import os
import glob
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

    # 生成TypeScript代码
    # 使用自定义的JSON编码器确保中文字符正确处理
    class CustomJSONEncoder(json.JSONEncoder):
        def encode(self, obj):
            # 使用ensure_ascii=False保持中文字符
            return json.dumps(obj, ensure_ascii=False, indent=2)

    ts_code = """export const config = {}

export default config
""".format(CustomJSONEncoder().encode(ts_config))

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_ts_file), exist_ok=True)

    # 写入TypeScript文件
    with open(output_ts_file, 'w', encoding='utf-8') as f:
        f.write(ts_code)

    return ts_config


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


def generate_overview_index(component_record, output_file):
    """生成概览index.ts文件"""
    # 生成TypeScript代码 - 使用format()而不是f-string避免反斜杠问题
    entries = []
    for key, value in component_record.items():
        entries.append(f'    {key}: \'{value}\'')

    ts_code = """export const componentRecord = {{
{}
}}
""".format(',\n'.join(entries))

    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # 写入TypeScript文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(ts_code)

    print(f"\n已生成概览文件: {output_file}")


def main():
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 输出目录（frontend/src/extensions/）
    output_base_dir = os.path.join(os.path.dirname(script_dir), 'frontend', 'src', 'extensions')

    print(f"脚本目录: {script_dir}")
    print(f"输出目录: {output_base_dir}")

    # 查找所有YAML文件
    yml_files = find_all_yml_files(script_dir)

    if not yml_files:
        print("未找到任何YML文件")
        return

    print(f"找到 {len(yml_files)} 个YML文件:")

    component_record = {}
    successful_count = 0

    for yml_file, rel_path in yml_files:
        print(f"\n处理文件: {rel_path}")

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
        config = generate_ts_from_yaml(yml_file, output_ts_file)

        if config:
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
            successful_count += 1
        else:
            print(f"  ❌ 失败: {rel_path}")

    # 生成概览index.ts文件
    overview_file = os.path.join(output_base_dir, 'index.ts')
    generate_overview_index(component_record, overview_file)

    # 打印总结
    print(f"\n{'=' * 50}")
    print(f"处理完成:")
    print(f"  总共找到: {len(yml_files)} 个YML文件")
    print(f"  成功生成: {successful_count} 个组件")
    print(f"  失败: {len(yml_files) - successful_count} 个")

    if component_record:
        print(f"\n生成的组件:")
        for key, value in sorted(component_record.items()):
            print(f"  {key}: '{value}'")


if __name__ == "__main__":
    main()