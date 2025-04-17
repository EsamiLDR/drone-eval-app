import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import yaml
from openai import OpenAI
import re
import threading
import os
import math
import sys

def get_resource_path(relative_path):
    """获取打包后资源文件的绝对路径"""
    if getattr(sys, 'frozen', False):  # 打包后的环境
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)



class StartPage:
    def __init__(self, root, main_app):
        self.root = root
        self.main_app = main_app
        self.frame = ttk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        # 设置界面尺寸
        self.root.geometry("1125x800")

        # 标题
        title = ttk.Label(
            self.frame,
            text="BANZUJI智能蜂群无人机试验系统软件",
            font=("黑体", 24, "bold"),
            foreground="#2c3e50"
        )
        title.pack(pady=40)

        # 图片容器
        img_frame = ttk.Frame(self.frame)
        img_frame.pack(fill=tk.BOTH, expand=True)

        # 加载图片
        try:
            self.bg_image = tk.PhotoImage(file=get_resource_path("pic1.png"))
            img_label = ttk.Label(img_frame, image=self.bg_image)
            img_label.pack()
        except Exception as e:
            messagebox.showerror("图片加载错误", f"无法加载启动图片: {str(e)}")

        # 开始按钮（透明样式）
        start_btn = ttk.Label(
            img_frame,
            text="开始测试",
            font=("微软雅黑", 18, "bold"),
            foreground="#2980b9",
            cursor="hand2"
        )
        start_btn.place(relx=0.9, rely=0.9, anchor=tk.SE)
        start_btn.bind("<Button-1>", self.start_main_app)

    def start_main_app(self, event):
        """销毁启动界面并显示主界面"""
        self.frame.destroy()
        self.main_app.create_phase1_ui()
        self.root.geometry("1200x900")

class DroneEvaluationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BANZUJI智能蜂群无人机试验系统软件 v6.0")
        self.input_values = {}  # 存储最终输入值的字典
        self.input_cache = {}  # 新增：数值缓存字典
        self.current_metric = None  # 新增：当前选中指标
        self.selected_second_level_metrics = []

        # 先创建启动界面
        self.start_page = StartPage(root, self)

        # 以下初始化延迟到点击开始按钮后执行
        self.phase1_frame = None
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "sk-91e2a47de58c40b0be17453cf90eb746"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
        )

        # 加载预定义指标
        with open(get_resource_path("newprompts.yaml"), 'r', encoding='utf-8') as f:
            self.all_metrics = yaml.safe_load(f)['phases']['phase1']

        with open(get_resource_path("newprompts.yaml"), 'r', encoding='utf-8') as f:
            self.metric_descriptions = yaml.safe_load(f)['metric_descriptions']

        #self.metric_descriptions = self.parse_metric_descriptions()
        self.predefined_metrics = {
            "支撑技术指标": ["平台技术", "布设技术", "通信技术", "导航技术",
                             "感知技术", "协同技术", "地面控制技术", "毁伤技术"],
                "涌现性指标": ["通信", "导航", "感知", "打击", "扩展", "决策", "抗毁", "控制"],
            "作战效能指标": ["抵近立体侦察效能", "全方位饱和攻击效能", "伴随式掩护效能"]
        }
        # 界面初始化
        self.phase2_frame = None
        self.phase1_final_content = ""
        self.metric_status = {}
        self.streaming_active = False  # 新增流式状态标识

    def create_phase1_ui(self):
        """创建第一阶段界面"""
        self.phase1_frame = ttk.Frame(self.root)
        self.phase1_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        # 任务描述输入
        ttk.Label(self.phase1_frame, text="任务描述:").grid(row=0, column=0, sticky=tk.W)
        self.mission_desc = tk.Text(self.phase1_frame, height=5, width=100)
        self.mission_desc.grid(row=1, column=0, columnspan=2, pady=5)

        # 操作按钮
        self.analyze_btn = ttk.Button(
            self.phase1_frame,
            text="生成评估指标",
            command=self.start_phase1_analysis
        )
        self.analyze_btn.grid(row=2, column=0, pady=10, sticky=tk.W)

        # 创建分割面板
        self.paned = ttk.PanedWindow(self.phase1_frame, orient=tk.VERTICAL)
        self.paned.grid(row=3, column=0, columnspan=2, sticky='nsew', pady=10)

        # 思维链展示区域
        thinking_frame = ttk.LabelFrame(self.paned, text="实时思维链")
        self.thinking_area = scrolledtext.ScrolledText(
            thinking_frame,
            wrap=tk.WORD,
            height=10,
            state=tk.DISABLED
        )
        self.thinking_area.pack(fill=tk.BOTH, expand=True)
        self.paned.add(thinking_frame, weight=1)

        # 结果展示区域
        result_frame = ttk.LabelFrame(self.paned, text="指标选择与权重分配结果")
        self.final_result = scrolledtext.ScrolledText(
            result_frame,
            wrap=tk.WORD,
            height=10,
            state=tk.DISABLED
        )
        self.final_result.pack(fill=tk.BOTH, expand=True)
        self.paned.add(result_frame, weight=1)

        # 设置初始分割比例
        self.paned.sashpos(0, 400)

        self.phase1_frame.rowconfigure(3, weight=1)
        self.phase1_frame.columnconfigure(0, weight=1)

        # 下一步按钮（初始隐藏）
        self.next_btn = ttk.Button(
            self.phase1_frame,
            text="下一步",
            command=self.switch_to_phase2,
            state=tk.DISABLED
        )
        self.next_btn.grid(row=4, column=1, pady=10, sticky=tk.SE)

        # 配置网格权重
        self.phase1_frame.rowconfigure(3, weight=1)
        self.phase1_frame.columnconfigure(0, weight=1)
        self.phase1_frame.columnconfigure(1, weight=1)

    def switch_to_phase2(self):
        """切换到第二阶段界面"""
        self.parse_selected_metrics()
        # 完全销毁第一阶段框架及其子组件
        if hasattr(self, 'phase1_frame'):
            self.phase1_frame.destroy()
            del self.phase1_frame  # 删除引用
        self.create_phase2_ui()

    def start_phase1_analysis(self):
        """启动第一阶段分析"""
        mission = self.mission_desc.get("1.0", tk.END).strip()
        if not mission:
            messagebox.showwarning("输入错误", "请输入任务描述")
            return

        self.analyze_btn.config(state=tk.DISABLED)
        self._update_thinking("模型思考中，请稍候...\n", clear=True)
        self.update_final_result("等待生成结果...\n", clear=True)  # 改为调用正确方法

        threading.Thread(
            target=self.run_phase1_analysis,
            args=(mission,),
            daemon=True
        ).start()

    def run_phase1_analysis(self, mission):
        """执行第一阶段API调用（流式处理）"""
        try:
            prompt = self.all_metrics + f"\n任务描述：{mission}"
            self.streaming_active = True  # 新增流式状态标识

            stream = self.client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[
                    {"role": "system", "content": "你是一位军事自动化与兵器计算领域的专家"},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
            )

            #with open('example.yaml', 'r', encoding='utf-8') as f:
                #full_content = yaml.safe_load(f)['example']

            full_content = ''
            for chunk in stream:
                if not self.streaming_active:  # 添加提前终止检查
                    break

                #break

                # 处理思维链内容
                reasoning = getattr(chunk.choices[0].delta, 'reasoning_content', '')
                if reasoning:
                    self.root.after(0, self._update_thinking, reasoning, False)

                # 处理最终内容（关键修复：恢复实时更新）
                content = getattr(chunk.choices[0].delta, 'content', '')
                if content:
                  full_content += content
                  #self.root.after(0, self._update_final_streaming, content)  # 新增实时更新方法

            self.phase1_final_content = full_content
            self.root.after(0, self.process_final_result)

        except Exception as e:
            self.root.after(0, messagebox.showerror, "API错误", str(e))
        finally:
            self.streaming_active = False
            self.root.after(0, self.analyze_btn.config, {'state': tk.NORMAL})

    def _update_final_streaming(self, content):
        """实时更新phase1结果区域"""
        self.final_result.config(state=tk.NORMAL)
        self.final_result.insert(tk.END, content)
        self.final_result.see(tk.END)
        self.final_result.config(state=tk.DISABLED)
        self.root.update_idletasks()  # 强制刷新UI

    def process_final_result(self):
        """处理最终结果并解析指标"""
        try:
            self.parse_selected_metrics()
            formatted_content = self.format_output_content(self.phase1_final_content)
            self.update_final_result(formatted_content, clear=True)  # 使用正确方法
            self.next_btn.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("错误", f"结果处理失败: {str(e)}")

    def format_output_content(self, original_content):
        """使用正则表达式转换输出格式"""
        try:
            lines = original_content.strip().split('\n')
            task_desc = lines[0] if lines else ''
            output = [task_desc]
            current_category = None
            categories = []

            # 处理每一行时检测终止标记
            for line in lines[1:]:
                line = line.strip()
                # 遇到权重验证或总结段落立即停止处理
                if re.match(r'^(权重验证|该权重分配)', line):
                    break

                # 匹配指标类别
                if re.match(r'^[一二三四五六七八九十]+、', line):
                    if current_category:
                        categories.append(current_category)
                    title = re.sub(r'（权重\d+%）', '', line)
                    current_category = {
                        'title': title,
                        'sub_items': [],
                        'other_lines': []
                    }
                else:
                    if current_category is not None:
                        # 匹配子指标项（增强正则兼容性）
                        sub_match = re.match(
                            r'^\d+\.\s+([^（]+?)\s*（\s*(\d+)%\s*）\s*-?\s*(.+)$',
                            line
                        )
                        if sub_match:
                            name, weight, desc = sub_match.groups()
                            current_category['sub_items'].append({
                                'name': name.strip(),
                                'weight': int(weight),
                                'desc': desc.strip()
                            })
                        elif line:
                            current_category['other_lines'].append(line)

            if current_category:
                categories.append(current_category)

            # 重组分类内容
            for cat in categories:
                sub_items = cat['sub_items']
                if not sub_items:
                    continue

                # 分割重点/其次考察（保持原顺序）
                sorted_subs = sorted(sub_items, key=lambda x: x['weight'], reverse=True)
                total = len(sorted_subs)
                split_index = total // 2

                output.append('')
                output.append(cat['title'])
                output.append('重点考察：')

                # 重点考察部分取前split_index项
                for idx, item in enumerate(sorted_subs[:split_index], 1):
                    output.append(f"{idx}. {item['name']}- {item['desc']}")

                output.append('其次考察：')
                # 其次考察部分从split_index开始，保持原始顺序
                remaining_items = [item for item in sub_items
                                   if item['name'] not in {x['name'] for x in sorted_subs[:split_index]}]

                for idx, item in enumerate(remaining_items, split_index + 1):
                    output.append(f"{idx}. {item['name']}- {item['desc']}")

            return '\n'.join(line for line in output if line.strip())

        except Exception as e:
            return f"格式转换错误：{str(e)}\n原始内容：\n{original_content}"

    def parse_selected_metrics(self):
        # 使用更精确的正则表达式匹配"1. 布设技术（权重15%）"等格式
        pattern = r'\d+\.\s*([^（]+?)\s*（\d+%）'
        matches = re.findall(pattern, self.phase1_final_content, re.UNICODE)
        # 过滤多余项
        self.selected_second_level_metrics = [
            name.strip() for name in matches if name.strip() not in ['承袭类', '非承袭类']
        ]

    def create_phase2_ui(self):
        """创建新版第二阶段界面（基于treeview的树结构）"""
        self.phase2_frame = ttk.Frame(self.root)
        self.phase2_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)

        # 创建左右分栏容器（显示为两列）
        self.main_paned = ttk.PanedWindow(self.phase2_frame, orient=tk.HORIZONTAL)
        self.main_paned.pack(fill=tk.BOTH, expand=True)

        # 左侧指标树
        self.left_panel = ttk.Frame(self.main_paned)
        style = ttk.Style()
        style.configure("Treeview", font=('宋体', 10), rowheight=25)
        self.tree = ttk.Treeview(self.left_panel, show="tree", style="Treeview")
        self.tree.heading("#0", text="指标名称")
        self.tree.pack(fill="both", expand=True)
        self.main_paned.add(self.left_panel, weight=1)

        # 右侧面板（描述文本 + 输入框 + 评估按钮）
        self.right_panel = ttk.Frame(self.main_paned)

        # 创建右侧垂直分割面板
        right_paned = ttk.PanedWindow(self.right_panel, orient=tk.VERTICAL)
        right_paned.pack(fill=tk.BOTH, expand=True)

        # 上方描述文本区域（占7份）
        self.text_area = tk.Text(
            right_paned,
            wrap="word",
            state="disabled",
            font=("宋体", 12),
            padx=10,
            pady=10
        )
        right_paned.add(self.text_area, weight=7)  # 上方占7份

        # 下方输入区域（占3份）
        bottom_frame = ttk.Frame(right_paned)

        # 输入框和单位标签
        self.input_frame = ttk.Frame(bottom_frame)
        self.entry = tk.Entry(self.input_frame, font=("Arial", 12), width=30)
        ttk.Label(self.input_frame, text="输入分数: ").pack(side=tk.LEFT, padx=5)
        self.entry.pack(side=tk.LEFT, padx=5)
        self.unit_label = ttk.Label(self.input_frame, text="", foreground="gray")  # 单位标签
        self.unit_label.pack(side=tk.LEFT)
        self.input_frame.pack(side=tk.TOP, fill=tk.X, pady=5)  # 输入框居中显示
        self.input_frame.pack_forget()  # 默认隐藏

        # 评估按钮
        self.next_btn = ttk.Button(
            bottom_frame,
            text="开始评估",
            command=self.validate_before_evaluate,
            state=tk.DISABLED
        )
        self.next_btn.pack(side=tk.BOTTOM, anchor=tk.CENTER, pady=10)  # 按钮居中显示

        right_paned.add(bottom_frame, weight=3)  # 下方占3份

        # 添加右侧整体到 PanedWindow
        self.main_paned.add(self.right_panel, weight=2)  # 右侧占比更大

        # 其余原有代码保持不变...
        self.node_desc = {}
        self.root_node_ids = []
        self._init_treeview_from_yaml()
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.tree.bind("<ButtonRelease-1>", self.on_tree_click)

        # 事件绑定和输入验证
        self.entry.bind('<KeyRelease>', self.on_entry_change)

        # 标记选中的指标并计算默认分数
        self.mark_selected_metrics()
        self.update_secondary_scores()
        self._update_evaluate_button_state()

    def _init_treeview_from_yaml(self):
        for main_key, main_value in self.metric_descriptions.items():
            root_node = self.tree.insert("", 'end', text=main_key, open=True)
            self.root_node_ids.append(root_node)

            # 初始化根节点在 node_desc 中的条目
            self.node_desc[root_node] = {
                "desc": main_value["desc"],
                "is_leaf": False,
                "metric_name": main_key,
                "original_text": main_key,
                "weight": 1.0  # 根节点权重默认为1.0（不影响实际计算）
            }

            is_emergent = (main_key == "涌现性指标")
            self._insert_sub_metrics(root_node, main_value["sub_metrics"], is_emergent)

    def _insert_sub_metrics(self, parent_node, sub_metrics, is_emergent=False):
        for key, meta in sub_metrics.items():
            item_id = self.tree.insert(parent_node, 'end', text=key, open=is_emergent)
            metric_name = key.strip()
            is_leaf = 'sub_metrics' not in meta  # 是否是叶子节点

            parent_id = self.tree.parent(item_id)  # 父节点ID
            original_text = key  # 初始文本
            is_secondary = False
            symbol = ''

            # 判断是否为二级指标并添加符号
            if parent_id in self.root_node_ids:
                # 判断父节点是否是支撑/作战主类（非涌现性指标）
                parent_text = self.tree.item(parent_id)['text']
                if parent_text in ['支撑技术指标', '作战效能指标']:
                    is_secondary = True
                    if metric_name in self.selected_second_level_metrics:
                        symbol = " √"
                    else:
                        symbol = " ×"
            else:
                # 处理涌现性指标的子节点（承袭类/非承袭类的下级）
                grandparent_id = self.tree.parent(parent_id)
                if grandparent_id and grandparent_id in self.root_node_ids:
                    grandparent_text = self.tree.item(grandparent_id)['text']
                    if grandparent_text == '涌现性指标':
                        # 父节点必须是承袭类或非承袭类
                        parent_info = self.node_desc.get(parent_id, {})
                        if parent_info.get('metric_name') in ['承袭类', '非承袭类']:
                            # 判断当前节点自身是否被选中
                            if metric_name in self.selected_second_level_metrics:
                                symbol = " √"
                            else:
                                symbol = " ×"
                            is_secondary = True

            # 更新节点显示文本
            if is_secondary:
                original_text += symbol
            self.tree.item(item_id, text=original_text)

            self.node_desc[item_id] = {
                'desc': meta.get('desc', ''),
                'is_leaf': is_leaf,
                'metric_name': metric_name,
                'original_text': key,
                'weight': meta.get('weight', 1.0),
                'unit': meta.get('unit', ''),  # 新增单位字段
                'conversion': meta.get('conversion_rule', {})  # 新增转换规则
            }

            if 'sub_metrics' in meta:
                self._insert_sub_metrics(item_id, meta['sub_metrics'], is_emergent=is_emergent)

    def mark_selected_metrics(self):
        """根据Phase1的输出标记被选中的二级指标"""
        selected = self.selected_second_level_metrics  # 从Phase1的parse_selected_metrics传入
        for item in self.tree.get_children():
            self._update_mark_status(item, self.selected_second_level_metrics)

    def _update_mark_status(self, item_id, selected_list):
        node_info = self.node_desc.get(item_id, {})
        parent_id = self.tree.parent(item_id)
        is_leaf = node_info.get('is_leaf', False)
        metric_name = node_info.get('metric_name', '')

        # 判断是否为二级指标
        is_secondary = False

        if parent_id in self.root_node_ids:
            # 父节点是主类根节点
            parent_text = self.tree.item(parent_id)['text']
            if parent_text in ['支撑技术指标', '作战效能指标']:
                is_secondary = True
        else:
            # 非主类子节点，检查是否为涌现性指标下的子类（承袭/非承袭）的子节点
            grandparent_id = self.tree.parent(parent_id)
            if grandparent_id and grandparent_id in self.root_node_ids:
                grandparent_text = self.tree.item(grandparent_id)['text']
                if grandparent_text == '涌现性指标':
                    # 父节点必须是承袭类或非承袭类
                    parent_info = self.node_desc.get(parent_id, {})
                    parent_metric_name = parent_info.get('metric_name', '')
                    if parent_metric_name in ['承袭类', '非承袭类']:
                        is_secondary = True

        original_text = node_info.get('original_text', '')  # 获取原始文本

        if is_secondary:
            # 添加符号，但防止重复添加
            symbol = "√" if metric_name in selected_list else "×"
            if not original_text.endswith(symbol):
                new_text = f"{original_text} {symbol}" if symbol in ['√', '×'] else original_text
                self.tree.item(item_id, text=new_text)
                self.node_desc[item_id]['original_text'] = new_text  # 更新存储的文本
        else:
            # 非二级指标直接保留原有文本
            new_text = original_text  # 必须在此处定义，否则下方循环会引用未定义的new_text？

        # 递归子节点
        for child in self.tree.get_children(item_id):
            self._update_mark_status(child, selected_list)

    def create_detail_panel(self):
        """创建右侧详细信息面板"""
        panel = ttk.Frame(self.main_paned)

        # 详细信息区域
        self.detail_header = ttk.Label(
            panel,
            font=("微软雅黑", 12, "bold"),
            wraplength=400
        )
        self.detail_header.pack(pady=10, fill=tk.X)

        self.detail_desc = scrolledtext.ScrolledText(
            panel,
            wrap=tk.WORD,
            height=8,
            state=tk.DISABLED
        )
        self.detail_desc.pack(fill=tk.BOTH, expand=True)

        # 输入区域
        self.input_frame.pack(fill=tk.X, pady=10)
        return panel

    def on_tree_select(self, event):
        selected_item = self.tree.focus()
        node_info = self.node_desc.get(selected_item, {})
        desc = node_info.get('desc', '')

        # 更新单位显示
        unit = node_info.get('unit', '')
        self.unit_label.config(text=unit if unit and unit != "无" else "")

        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete(1.0, tk.END)
        self.text_area.insert(tk.END, desc)
        self.text_area.config(state=tk.DISABLED)

        is_leaf = node_info.get('is_leaf', False)
        conv_type = node_info.get('conversion', {}).get('type', 'direct')

        # 隐藏所有输入框
        self.input_frame.pack_forget()
        if hasattr(self, 'multi_input_frame'):
            self.multi_input_frame.pack_forget()

        # 检查是否为选中的二级指标的叶子节点
        parent_id = self.tree.parent(selected_item)
        secondary_parent = None
        while parent_id != '':
            parent_info = self.node_desc.get(parent_id, {})
            parent_metric_name = parent_info.get('metric_name', '')

            if parent_metric_name in self.selected_second_level_metrics:
                secondary_parent = parent_metric_name
                break

            parent_id = self.tree.parent(parent_id)

        if is_leaf and secondary_parent in self.selected_second_level_metrics:
            # 根据转换类型显示不同的输入框
            if conv_type == 'emergent':
                fields = node_info.get('conversion', {}).get('fields', [])
                if fields:  # 确保有字段需要显示
                    self._create_multi_input_frame(fields)
                    self.multi_input_frame.pack(fill=tk.X, pady=5)  # 显示多输入框

                    # 填入已有值
                    current_values = self.input_values.get(selected_item, {})
                    for key, entry in self.multi_entries.items():
                        entry.delete(0, tk.END)
                        if key in current_values:
                            entry.insert(0, str(current_values[key]))
            else:
                # 非涌现性指标显示单一输入框
                self.input_frame.pack(fill=tk.X, pady=5)
                current_value = self.input_values.get(selected_item, "")
                self.entry.delete(0, tk.END)
                self.entry.insert(0, current_value)
        else:
            self.entry.delete(0, tk.END)

    def _create_multi_input_frame(self, fields):
        """创建多个输入框的框架，使用网格布局均匀分布"""
        if hasattr(self, 'multi_input_frame'):
            self.multi_input_frame.destroy()

        # 获取bottom_frame
        bottom_frame = self.right_panel.winfo_children()[0].winfo_children()[1]
        self.multi_input_frame = ttk.Frame(bottom_frame)
        self.multi_input_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.multi_entries = {}

        # 计算每行显示的输入框数量
        if len(fields) == 6:
            cols = 3  # 特例：6个输入框每行3个
        else:
            cols = 2
        rows = (len(fields) + cols - 1) // cols  # 计算需要的行数

        for i, field in enumerate(fields):
            row = i // cols
            col = i % cols

            # 创建标签和输入框的容器
            field_frame = ttk.Frame(self.multi_input_frame)
            field_frame.grid(row=row, column=col, padx=5, pady=2, sticky="w")

            # 标签
            label = ttk.Label(field_frame, text=f"{field['name']}:", width=15, anchor=tk.W)
            label.pack(side=tk.LEFT)

            # 输入框
            entry = tk.Entry(field_frame, font=("Arial", 10), width=10)
            entry.pack(side=tk.LEFT, padx=5)
            entry.bind('<KeyRelease>', self.on_entry_change)  # 添加事件绑定

            # 单位标签
            if 'unit' in field:
                unit_label = ttk.Label(field_frame, text=field['unit'], foreground="gray")
                unit_label.pack(side=tk.LEFT)

            self.multi_entries[field['key']] = entry

        return self.multi_input_frame

    def on_entry_change(self, event):
        current_node = self.tree.focus()
        if not current_node:
            return

        node_info = self.node_desc.get(current_node, {})
        conv_type = node_info.get('conversion', {}).get('type', 'direct')

        if conv_type == 'emergent':
            # 检查所有输入框是否都已填写
            all_filled = True
            inputs = {}

            for key, entry in self.multi_entries.items():
                value = entry.get().strip()
                if not value:
                    all_filled = False
                    break

                field = next((f for f in node_info['conversion']['fields'] if f['key'] == key), None)
                if field:
                    if field.get('type') == 'grade':
                        mapping = field.get('mapping', {})
                        inputs[key] = mapping.get(value, 0)
                    elif field.get('type') == 'binary':
                        if value not in ['0', '1']:
                            all_filled = False
                            break
                        inputs[key] = int(value)
                    else:
                        if not value.replace('.', '', 1).isdigit():
                            all_filled = False
                            break
                        inputs[key] = float(value)

            if all_filled:
                self.input_values[current_node] = inputs
            else:
                self.input_values[current_node] = None
        else:
            value_str = self.entry.get().strip()
            converted_value = self._convert_value(
                value_str,
                node_info.get('conversion', {})
            )

            if 0 <= converted_value <= 100:
                self.input_values[current_node] = converted_value
            else:
                self.input_values[current_node] = None
                self.entry.delete(0, tk.END)

        self.update_secondary_scores()
        self._update_evaluate_button_state()

    def _convert_value(self, value_str, conversion):
        """扩展的值转换方法，支持涌现性指标"""
        rule_type = conversion.get('type', 'direct')

        try:
            if rule_type == 'emergent':
                # 检查所有输入框是否都已填写
                fields = conversion.get('fields', [])
                inputs = {}

                for field in fields:
                    entry = self.multi_entries.get(field['key'])
                    if not entry:
                        return 0

                    value = entry.get().strip()
                    if not value:  # 如果有一个输入框为空
                        return 0

                    if field.get('type') == 'grade':
                        mapping = field.get('mapping', {})
                        inputs[field['key']] = mapping.get(value, 0)
                    elif field.get('type') == 'binary':
                        if value not in ['0', '1']:
                            return 0
                        inputs[field['key']] = int(value)
                    else:
                        if not value.replace('.', '', 1).isdigit():
                            return 0
                        inputs[field['key']] = float(value)

                # 执行计算公式
                formula = conversion.get('formula', '0')
                try:
                    result = eval(formula, {}, inputs)
                    return 1 if result else 0
                except Exception as e:
                    print(f"公式计算错误: {e}")
                    return 0

            # 原有转换逻辑保持不变
            elif rule_type == 'range':
                value = float(value_str)
                for condition in conversion.get('ranges', []):
                    if eval(condition['condition'], {'value': value}):
                        return condition['score']
                return 0

            elif rule_type == 'linear':
                value = float(value_str)
                return min(100, max(0, eval(conversion['formula'], {'value': value})))

            elif rule_type == 'grade':
                return conversion['mapping'].get(value_str.strip(), 0)

            elif rule_type == 'direct':
                return int(value_str) if value_str.isdigit() else 0

        except Exception as e:
            print(f"值转换错误: {e}")
            return 0

    def _update_evaluate_button_state(self):
        valid = True
        for metric in self.selected_second_level_metrics:
            node_id = self._find_node_by_metric_name(metric)
            if not node_id:
                valid = False
                continue

            node_info = self.node_desc.get(node_id, {})
            metric_type = self._get_current_metric_type(node_id)

            if metric_type == '涌现性指标':
                # 检查所有子节点是否都已填写
                leaves = self._get_all_leaf_nodes(node_id)
                for leaf in leaves:
                    if leaf not in self.input_values or self.input_values[leaf] is None:
                        valid = False
                        break
                    if isinstance(self.input_values[leaf], dict):
                        # 检查字典中是否有None值
                        if None in self.input_values[leaf].values():
                            valid = False
                            break
            else:
                # 非涌现性指标检查
                score = self.input_cache.get(metric, -1.0)
                if isinstance(score, (type(None), float)) and score == -1.0:
                    valid = False

        state = tk.NORMAL if valid else tk.DISABLED
        self.next_btn.config(state=state)

    def _get_current_metric_type(self, node_id):
        """获取当前节点所属的指标类别（如涌现性指标）"""
        parent = self.tree.parent(node_id)
        if parent in self.root_node_ids:
            return self.tree.item(parent)['text']
        else:
            return self._get_current_metric_type(parent)

    def _validate_value(self, value_str, node_id):
        node_info = self.node_desc.get(node_id, {})
        conv_type = node_info.get('conversion', {}).get('type', 'direct')

        # 针对转换类型进行验证
        if conv_type == 'grade':
            valid_values = list(node_info['conversion'].get('mapping', {}).keys())
            return value_str in valid_values
        elif conv_type == 'range':
            try:
                float(value_str)
                return True
            except ValueError:
                return False
        elif conv_type == 'linear':
            try:
                float(value_str)
                return True
            except ValueError:
                return False
        else:  # 原百分制验证
            return value_str.isdigit() and 0 <= int(value_str) <= 100

    def _is_secondary_node(self, node_id):
        metric_name = self.node_desc.get(node_id, {}).get('metric_name', '')
        return metric_name in self.selected_second_level_metrics

    def _get_all_leaf_nodes(self, node_id):
        leaves = []
        children = self.tree.get_children(node_id)
        if not children:
            leaves.append(node_id)
            return leaves
        for child in children:
            leaves.extend(self._get_all_leaf_nodes(child))
        return leaves

    def calculate_secondary_score(self, node_id):
        leaves = self._get_all_leaf_nodes(node_id)
        valid_values, weights = [], []
        total_weight = 0.0

        metric_type = self._get_current_metric_type(node_id)

        for leaf in leaves:
            converted_value = self.input_values.get(leaf, None)
            leaf_weight = self.node_desc[leaf].get('weight', 1.0)

            if metric_type == '涌现性指标':
                if isinstance(converted_value, dict):
                    # 检查所有字段是否已填写
                    if None in converted_value.values():
                        return None
                    # 执行计算公式
                    formula = self.node_desc[leaf].get('conversion', {}).get('formula', '0')
                    try:
                        result = eval(formula, {}, converted_value)
                        valid_values.append(1 if result else 0)
                    except Exception:
                        valid_values.append(0)
                else:
                    return None
            else:
                if converted_value is None or not (0 <= converted_value <= 100):
                    return None
                valid_values.append(float(converted_value))

            weights.append(leaf_weight)
            total_weight += leaf_weight

        if not valid_values or total_weight == 0:
            return None

        score = round(sum(v * w for v, w in zip(valid_values, weights)) / total_weight, 1)
        return score if not math.isnan(score) else None

    def update_secondary_scores(self):
        input_cache = {}
        secondary_nodes = self.get_secondary_metrics()
        for node in secondary_nodes:
            score = self.calculate_secondary_score(node)
            original_text = self.tree.item(node, "text").split("[")[0].strip()
            new_text = f"{original_text} [ 已填写 ]" if score is not None else f"{original_text} [ - ]"
            self.tree.item(node, text=new_text)
            metric_name = self.node_desc[node]['metric_name']
            input_cache[metric_name] = score if score is not None else -1.0

            # 打印一级指标计算结果
            '''
            if score is not None:
                print("\n=== 一级指标计算结果 ===")
                print(f"指标名称: {metric_name}")
                print(f"得分: {score}")
            '''

        self.input_cache = input_cache
        self._update_evaluate_button_state()

    def get_secondary_metrics(self):
        """获取所有有效二级指标节点的item_id列表"""
        secondary_metrics = []
        # 遍历所有节点
        for node in self.tree.get_children():
            self._collect_secondary_metrics(node, secondary_metrics)
        return secondary_metrics

    def _collect_secondary_metrics(self, node_id, result_list):
        """递归收集所有属于二级指标的叶节点"""
        children = self.tree.get_children(node_id)
        if not children:
            return  # 叶节点，不参与二级指标收集

        is_secondary = self._is_secondary_node(node_id)
        if is_secondary:
            result_list.append(node_id)
        else:
            for child in children:
                self._collect_secondary_metrics(child, result_list)

    def _update_score(self, node_id, score):
        """直接更新指定二级指标节点的文本和得分"""
        original_text = self.tree.item(node_id, "text").split("[")[0].strip()
        if score is not None:
            new_text = f"{original_text} [ {score} ]"
        else:
            new_text = f"{original_text} [ - ]"
        self.tree.item(node_id, text=new_text)

    def validate_before_evaluate(self):
        # 调用 _update_evaluate_button_state 前确保缓存里有值
        self.update_secondary_scores()
        selected_metrics = self.selected_second_level_metrics
        valid = True
        error_metrics = []
        for metric in selected_metrics:
            node_id = self._find_node_by_metric_name(metric)
            if not node_id:
                valid = False
                error_metrics.append(metric)
                continue
            current_score = self.input_cache.get(metric, -1.0)
            if current_score == -1.0 or current_score is None:
                valid = False
                error_metrics.append(metric)
        if not valid:
            errors = "、".join(error_metrics)
            messagebox.showerror("输入无效",
                                f"请补全或修正以下指标：\n{errors}\n\n"
                                "确保所有叶子节点的数值符合要求",
                                parent=self.right_panel)
        else:
            self._create_evaluation_window()

    def _find_node_by_metric_name(self, target_name):
        found_id = None

        def dfs(node):
            nonlocal found_id
            node_info = self.node_desc.get(node, {})
            if node_info['metric_name'] == target_name:
                found_id = node
            children = self.tree.get_children(node)
            for child in children:
                dfs(child)

        for root in self.tree.get_children():
            dfs(root)
        return found_id

    def _find_in_subtree(self, node_id, target_name):
        current_info = self.node_desc.get(node_id, {})
        if current_info.get('metric_name', "") == target_name:
            self._found_node = node_id
            return
        for child in self.tree.get_children(node_id):
            self._find_in_subtree(child, target_name)

    def _create_evaluation_window(self):
        """在主线程创建评估窗口"""
        self.result_win = tk.Toplevel(self.root)
        self.result_win.title("评估结果")
        self.result_win.protocol("WM_DELETE_WINDOW", self._on_eval_window_close)  # 新增关闭事件绑定

        # 双区域布局
        paned = ttk.PanedWindow(self.result_win, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # 实时分析区域
        self.thinking_frame = ttk.LabelFrame(paned, text="分析过程")
        self.thinking_area = scrolledtext.ScrolledText(self.thinking_frame, wrap=tk.WORD)
        self.thinking_area.pack(fill=tk.BOTH, expand=True)
        paned.add(self.thinking_frame)

        # 最终结果区域
        self.result_frame = ttk.LabelFrame(paned, text="评估报告")
        self.result_area = scrolledtext.ScrolledText(self.result_frame, wrap=tk.WORD)
        self.result_area.pack(fill=tk.BOTH, expand=True)
        paned.add(self.result_frame)

        self._update_evaluation_thinking("模型思考中，请稍候...\n", clear=True)
        self._update_evaluation_result("等待评估结果...\n", clear=True)

        # 启动评估线程
        threading.Thread(
            target=self.run_phase2_evaluation,
            args=(self.input_cache,),
            daemon=True
        ).start()

    def _on_eval_window_close(self):
        """处理评估窗口关闭事件"""
        self.streaming_active = False  # 终止流式处理
        if self.result_win.winfo_exists():
            self.result_win.destroy()

    def on_tree_click(self, event):
        # 用户点击节点时重选或展开（可简化为 pass 以避免UI干扰）
        pass

    def show_tooltip(self, event, description):
        """显示工具提示"""
        x = event.widget.winfo_rootx() + event.x + 10
        y = event.widget.winfo_rooty() + event.y + 10

        self.tooltip = tk.Toplevel(event.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(
            self.tooltip,
            text=description,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padding=(5, 2),
            wraplength=300  # 自动换行
        )
        label.pack()

    def hide_tooltip(self, event=None):
        """隐藏工具提示"""
        if hasattr(self, 'tooltip') and self.tooltip:
            self.tooltip.destroy()
            del self.tooltip

    def run_phase2_evaluation(self, inputs):
        """改进的评估方法（添加窗口状态检查）"""
        try:
            self.streaming_active = True
            full_content = ""

            with open(get_resource_path("newprompts.yaml"), 'r', encoding='utf-8') as f:
                phase2_template = yaml.safe_load(f)['phases']['phase2']

            full_prompt = phase2_template.format(
                inputs=inputs,
                phase1_result=self.phase1_final_content
            )

            stream = self.client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[
                    {"role": "system", "content": "你是一位军事自动化与兵器计算领域的专家"},
                    {"role": "user", "content": full_prompt}
                ],
                stream=True,
            )

            for chunk in stream:
                # 双重检查：流状态和窗口存在性
                if not self.streaming_active or not self.result_win.winfo_exists():
                    break

                # 处理思维链内容
                reasoning = getattr(chunk.choices[0].delta, 'reasoning_content', '')
                if reasoning:
                    self._safe_update_thinking(reasoning, False)  # 改为安全更新方法

                # 处理最终内容
                content = getattr(chunk.choices[0].delta, 'content', '')
                if content:
                    full_content += content
                    self._safe_update_result(content, False)  # 改为安全更新方法

        except Exception as e:
            if self.result_win.winfo_exists():
                self.root.after(0, messagebox.showerror, "评估错误", str(e))
        finally:
            self.streaming_active = False

    def _safe_update_thinking(self, content, clear=False):
        """安全更新思维链区域"""
        if self.result_win.winfo_exists():
            self.thinking_area.config(state=tk.NORMAL)
            if clear:
                self.thinking_area.delete(1.0, tk.END)
            self.thinking_area.insert(tk.END, content)
            self.thinking_area.see(tk.END)
            self.thinking_area.config(state=tk.DISABLED)

    def _safe_update_result(self, content, clear=False):
        """安全更新结果区域"""
        if self.result_win.winfo_exists():
            self.result_area.config(state=tk.NORMAL)
            if clear:
                self.result_area.delete(1.0, tk.END)
            self.result_area.insert(tk.END, content)
            self.result_area.see(tk.END)
            self.result_area.config(state=tk.DISABLED)

    def _update_thinking(self, content, clear=False):
        """更新phase1思维链区域"""
        self.thinking_area.config(state=tk.NORMAL)
        if clear:
            self.thinking_area.delete(1.0, tk.END)
        self.thinking_area.insert(tk.END, content)
        self.thinking_area.see(tk.END)
        self.thinking_area.config(state=tk.DISABLED)
        self.root.update_idletasks()  # 强制刷新UI

    def update_final_result(self, content, clear=False):
        """专用于更新phase1结果区域⭐"""
        self.final_result.config(state=tk.NORMAL)
        if clear:
            self.final_result.delete(1.0, tk.END)
        self.final_result.insert(tk.END, content)
        self.final_result.see(tk.END)
        self.final_result.config(state=tk.DISABLED)

    def _update_evaluation_thinking(self, content, clear=False):
        """改为使用安全更新"""
        self.root.after(0, self._safe_update_thinking, content, clear)

    def _update_evaluation_result(self, content, clear=False):
        """改为使用安全更新"""
        self.root.after(0, self._safe_update_result, content, clear)


if __name__ == "__main__":
    root = tk.Tk()
    app = DroneEvaluationApp(root)
    root.mainloop()
