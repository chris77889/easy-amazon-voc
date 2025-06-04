from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import csv
import json
from functions import  generate_doc_description, do_review,get_json_content

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB限制

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '未选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '空文件名'}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({'error': '仅支持CSV文件'}), 400
        
    # 检查CSV行数不超过100条
    file.seek(0)
    line_count = sum(1 for _ in csv.reader(file.read().decode('utf-8').splitlines()))
    if line_count > 30:
        return jsonify({'error': 'CSV文件数据不能超过30条'}), 400
    file.seek(0)

    # 保存原始文件
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(input_path)

    # 处理CSV文件
    output_filename = f'processed_{file.filename}'
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
     
    with open(input_path, 'r', newline='', encoding='utf-8') as infile, \
         open(output_path, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        # 处理表头
        headers = next(reader)
        target_column = headers.index('cr-original-review-content (2)')
        headers.append('用户需求与痛点-使用场景')  
        headers.append('用户需求与痛点-购买动机')
        headers.append('产品反馈-产品优点')  
        headers.append('产品反馈-产品缺点')  
        headers.append('产品反馈-用户期望建议')  
        headers.append('产品反馈-设计与外观')  
        headers.append('服务评价-物流配送')  
        headers.append('服务评价-售后服务') 
        headers.append('服务评价-售前服务') 
        headers.append('品牌形象与口碑-推荐意愿原因分析') 
        headers.append('品牌形象与口碑-是否愿意推荐给他人') 
        headers.append('品牌形象与口碑-品牌印象') 
        headers.append('感官感受') 
        headers.append('价格感知')  
        writer.writerow(headers)
        
        # 处理数据行
        whole_content = ""
        for row in reader:
            content = row[target_column] 
            whole_content += content + "\n"  # 拼接内容 
        print("完整内容：", whole_content)  # 打印拼接结果
        deal_whole_content = generate_doc_description(whole_content)
        print("处理内容meta：", deal_whole_content)

        infile.seek(0)  # 重置指针到文件开头
        for row in reader: 
            do_content = row[target_column] 
            do_things = do_review(do_content, deal_whole_content)
            print("处理do_things：", do_things)
            # 解析JSON数据
            try:
                do_things_dict = json.loads(get_json_content(do_things))
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {e}，内容：{do_things}")
                continue
            # 如果do_things_dict不是字典，则跳过
            if not isinstance(do_things_dict, dict):
                print(f"返回内容不是字典: {do_things_dict}")
                continue
            # 按表头顺序提取字段值（列表转字符串，逗号分隔）
            row.append(','.join(do_things_dict.get('人群场景', {}).get('用户需求与痛点-使用场景', [])))
            row.append(','.join(do_things_dict.get('人群场景', {}).get('用户需求与痛点-购买动机', [])))
            row.append(','.join(do_things_dict.get('功能价值', {}).get('产品反馈-产品优点', [])))
            row.append(','.join(do_things_dict.get('功能价值', {}).get('产品反馈-产品缺点', [])))
            row.append(','.join(do_things_dict.get('功能价值', {}).get('产品反馈-用户期望建议', [])))
            row.append(','.join(do_things_dict.get('功能价值', {}).get('产品反馈-设计与外观', [])))
            row.append(','.join(do_things_dict.get('保障价值', {}).get('服务评价-物流配送', [])))
            row.append(','.join(do_things_dict.get('保障价值', {}).get('服务评价-售后服务', [])))
            row.append(','.join(do_things_dict.get('保障价值', {}).get('服务评价-售前服务', [])))
            row.append(','.join(do_things_dict.get('体验价值', {}).get('品牌形象与口碑-推荐意愿原因分析', [])))
            row.append(','.join(do_things_dict.get('体验价值', {}).get('品牌形象与口碑-是否愿意推荐给他人', [])))
            row.append(','.join(do_things_dict.get('体验价值', {}).get('品牌形象与口碑-品牌印象', [])))
            row.append(','.join(do_things_dict.get('体验价值', {}).get('感官感受', [])))
            row.append(','.join(do_things_dict.get('体验价值', {}).get('价格感知', [])))
            writer.writerow(row) 

    # 词频分析
    word_frequency = {}
    with open(output_path, 'r', newline='', encoding='utf-8') as csvfile:
        for column in ['用户需求与痛点-使用场景', '用户需求与痛点-购买动机', '产品反馈-产品优点', 
                     '产品反馈-产品缺点', '产品反馈-用户期望建议', '产品反馈-设计与外观',
                     '服务评价-物流配送', '服务评价-售后服务', '服务评价-售前服务',
                     '品牌形象与口碑-推荐意愿原因分析', '品牌形象与口碑-是否愿意推荐给他人',
                     '品牌形象与口碑-品牌印象', '感官感受', '价格感知']:
            word_frequency[column] = {}
            csvfile.seek(0)  # 重置文件指针到开头
            reader = csv.DictReader(csvfile)
            for row in reader:
                words = row[column].split(',')
                for word in words:
                    word = word.strip()
                    if word:
                        word_frequency[column][word] = word_frequency[column].get(word, 0) + 1
            
            # 按词频从大到小排序
            word_frequency[column] = dict(
                sorted(
                    word_frequency[column].items(), 
                    key=lambda item: item[1], 
                    reverse=True
                )
            )
            csvfile.seek(0)  # 重置指针
    
    return jsonify({
        'filename': output_filename,
        'filepath': f'/download/{output_filename}',
        'wordFrequency': word_frequency
    })

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)