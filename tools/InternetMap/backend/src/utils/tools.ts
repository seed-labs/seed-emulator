import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';

export class File {

}

// 创建临时文件夹
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'pathName'));
console.log(`Temporary directory ${tempDir} created successfully!`);

// 创建临时文件路径
const tempFilePath = path.join(tempDir, 'temp-file.txt');

// 写入临时文件
fs.writeFileSync(tempFilePath, '这是一些测试文本。');

// 读取临时文件（可选）
const data = fs.readFileSync(tempFilePath, 'utf8');
console.log(data); // 输出: 这是一些测试文本。

// 删除临时文件
fs.unlinkSync(tempFilePath);

// 删除临时文件夹
fs.rmdirSync(tempDir);
