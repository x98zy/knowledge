# 上传知识文件功能实施文档

## 一、任务概述

在知识库文件列表页面（`FileList.vue`）添加「上传知识文件」按钮，点击后弹出对话框，用户选择文件并配置分段参数，依次调用后端两个接口完成文件上传与解析触发。

## 二、交互流程

```
点击「上传知识文件」按钮
        ↓
弹出上传对话框（选择文件 + 配置分段参数）
        ↓
点击「确定上传」
        ↓
步骤1：调用 POST /knowledge/upload_file （上传文件到 OSS）
        ↓  返回 file_key
步骤2：调用 POST /file/create （创建文件记录，触发解析）
        ↓
上传成功，关闭对话框，刷新文件列表
```

## 三、需要改动的文件

| 文件路径 | 改动类型 | 说明 |
|---------|---------|------|
| [api.js](file:///d:/knowledge/web/src/api.js) | 修改 | 新增 `createKnowledgeFile` 接口方法（`uploadFile` 已存在，无需修改） |
| [FileList.vue](file:///d:/knowledge/web/src/views/knowledge/FileList.vue) | 修改 | 添加「上传知识文件」按钮和上传对话框（含分段参数表单） |

## 四、具体改动内容

### 4.1 api.js 改动

#### 4.1.1 `uploadFile` 函数（无需修改）

当前 `uploadFile` 函数已满足需求，后端 `upload_file` 接口已移除 `knowledge_id` 参数，只需传递 `formData` 即可：

```javascript
export async function uploadFile(formData) {
  const res = await api.post('/knowledge/upload_file', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
```

#### 4.1.2 新增 `createKnowledgeFile` 函数

调用 `POST /file/create` 接口，传递分段配置参数。

```javascript
export async function createKnowledgeFile(data) {
  const res = await api.post('/file/create', data)
  return res.data
}
```

### 4.2 FileList.vue 改动

#### 4.2.1 页面头部添加按钮

在页面标题区域（`page-header`）右侧添加「上传知识文件」按钮：

```html
<div class="page-header">
  <div class="header-title">...</div>
  <el-button type="primary" @click="showUploadDialog = true">
    <el-icon><Upload /></el-icon>
    上传知识文件
  </el-button>
</div>
```

同时调整 `.page-header` 样式为 `flex` 布局（与 `List.vue` 保持一致）。

#### 4.2.2 添加上传对话框

对话框包含两部分：**文件选择** + **分段参数配置**。

```html
<el-dialog v-model="showUploadDialog" title="上传知识文件" width="600px" :close-on-click-modal="false">
  <el-form :model="uploadForm" :rules="uploadRules" ref="uploadFormRef" label-width="120px" label-position="left">
    
    <!-- 文件选择 -->
    <el-form-item label="选择文件" prop="file">
      <el-upload
        :auto-upload="false"
        :limit="1"
        :on-change="handleFileChange"
        :on-exceed="handleExceed"
      >
        <el-button type="primary">选择文件</el-button>
        <template #tip>
          <div class="el-upload__tip">支持 txt, md, pdf, docx, csv, xlsx, html 等格式</div>
        </template>
      </el-upload>
    </el-form-item>

    <!-- 分段模式 -->
    <el-form-item label="分段模式" prop="segment_mode">
      <el-select v-model="uploadForm.segment_mode" placeholder="请选择分段模式">
        <el-option label="通用分段" value="text_model" />
        <el-option label="QA分段" value="qa_model" />
        <el-option label="父子分段" value="hierarchical_model" />
      </el-select>
    </el-form-item>

    <!-- 预处理规则（多选） -->
    <el-form-item label="预处理规则" prop="pre_rule">
      <el-checkbox-group v-model="uploadForm.pre_rule_list">
        <el-checkbox label="remove_urls_emails">去除URL链接</el-checkbox>
        <el-checkbox label="remove_extra_spaces">去除多余空格</el-checkbox>
      </el-checkbox-group>
    </el-form-item>

    <!-- 分段最大长度 -->
    <el-form-item label="分段最大长度" prop="max_tokens">
      <el-input-number v-model="uploadForm.max_tokens" :min="1" :max="10000" />
    </el-form-item>

    <!-- 分段重叠长度 -->
    <el-form-item label="分段重叠长度" prop="overlap">
      <el-input-number v-model="uploadForm.overlap" :min="0" :max="1000" />
    </el-form-item>

    <!-- 分段分隔符 -->
    <el-form-item label="分段分隔符" prop="delimiter">
      <el-input v-model="uploadForm.delimiter" placeholder="如 \n\n" />
    </el-form-item>

    <!-- 以下字段仅在「父子分段」时显示 -->
    <template v-if="uploadForm.segment_mode === 'hierarchical_model'">
      <el-divider>父子分段配置</el-divider>
      <el-form-item label="父分段规则" prop="parent_mode">
        <el-input v-model="uploadForm.parent_mode" placeholder="请输入父分段规则" />
      </el-form-item>
      <el-form-item label="子分段分隔符" prop="child_delimiter">
        <el-input v-model="uploadForm.child_delimiter" placeholder="如 \n" />
      </el-form-item>
      <el-form-item label="子分段重叠长度" prop="child_overlap">
        <el-input-number v-model="uploadForm.child_overlap" :min="0" :max="1000" />
      </el-form-item>
      <el-form-item label="子分段最大长度" prop="child_max_tokens">
        <el-input-number v-model="uploadForm.child_max_tokens" :min="1" :max="10000" />
      </el-form-item>
    </template>

  </el-form>
  <template #footer>
    <el-button @click="showUploadDialog = false">取消</el-button>
    <el-button type="primary" :loading="uploading" @click="handleUpload">确定上传</el-button>
  </template>
</el-dialog>
```

#### 4.2.3 表单数据结构

```javascript
const uploadForm = reactive({
  file: null,              // 用户选择的文件对象
  segment_mode: 'text_model',  // 分段模式
  pre_rule_list: [],       // 预处理规则（数组，提交时拼接为字符串）
  max_tokens: 500,         // 分段最大长度
  overlap: 50,             // 分段重叠长度
  delimiter: '\\n\\n',     // 分段分隔符
  // 以下仅父子分段时有值
  parent_mode: '',         
  child_delimiter: '',
  child_overlap: 0,
  child_max_tokens: 200,
})
```

#### 4.2.4 表单验证规则

```javascript
const uploadRules = {
  file: [{ required: true, message: '请选择文件', trigger: 'change' }],
  segment_mode: [{ required: true, message: '请选择分段模式', trigger: 'change' }],
  max_tokens: [{ required: true, message: '请输入分段最大长度', trigger: 'blur' }],
  overlap: [{ required: true, message: '请输入分段重叠长度', trigger: 'blur' }],
  delimiter: [{ required: true, message: '请输入分段分隔符', trigger: 'blur' }],
}
```

#### 4.2.5 上传处理逻辑

```javascript
async function handleUpload() {
  // 1. 表单验证
  const valid = await uploadFormRef.value?.validate().catch(() => null)
  if (valid === null) return

  uploading.value = true
  try {
    // 2. 上传文件到 OSS
    const formData = new FormData()
    formData.append('file', uploadForm.file)
    const uploadRes = await uploadFile(formData)
    const fileKey = uploadRes.data.file_key

    // 3. 拼接 pre_rule（多选用分号分隔）
    const preRule = uploadForm.pre_rule_list.join(';')

    // 4. 创建文件记录，触发解析
    await createKnowledgeFile({
      dataset_id: knowledgeId,
      file_key: fileKey,
      enable_semantic: false,
      segment_mode: uploadForm.segment_mode,
      pre_rule: preRule,
      max_tokens: uploadForm.max_tokens,
      overlap: uploadForm.overlap,
      delimiter: uploadForm.delimiter,
      // 父子分段参数（仅父子分段时传递）
      parent_mode: uploadForm.segment_mode === 'hierarchical_model' ? uploadForm.parent_mode : null,
      child_delimiter: uploadForm.segment_mode === 'hierarchical_model' ? uploadForm.child_delimiter : null,
      child_overlap: uploadForm.segment_mode === 'hierarchical_model' ? uploadForm.child_overlap : null,
      child_max_tokens: uploadForm.segment_mode === 'hierarchical_model' ? uploadForm.child_max_tokens : null,
    })

    // 5. 成功提示并刷新列表
    ElMessage.success('文件上传成功，正在解析中...')
    showUploadDialog.value = false
    resetUploadForm()
    fetchList()
  } catch (e) {
    ElMessage.error(e.response?.data?.message || '文件上传失败')
  } finally {
    uploading.value = false
  }
}
```

## 五、参数映射表

| 前端字段 | 后端参数 | 类型 | 说明 |
|---------|---------|------|------|
| `uploadForm.file` | `file` (FormData) | File | 上传的文件 |
| `knowledgeId` | `dataset_id` | string | 知识库ID（从路由参数获取，创建文件时传递） |
| `uploadForm.file` → OSS返回 | `file_key` | string | OSS文件键名 |
| - | `enable_semantic` | bool | 是否智能分段，固定 `false` |
| `uploadForm.segment_mode` | `segment_mode` | string | `text_model` / `qa_model` / `hierarchical_model` |
| `uploadForm.pre_rule_list.join(';')` | `pre_rule` | string | 多选用分号拼接，如 `remove_urls_emails;remove_extra_spaces` |
| `uploadForm.max_tokens` | `max_tokens` | int | 分段最大长度 |
| `uploadForm.overlap` | `overlap` | int | 分段重叠长度 |
| `uploadForm.delimiter` | `delimiter` | string | 分段分隔符 |
| `uploadForm.parent_mode` | `parent_mode` | string\|null | 仅父子分段时有值 |
| `uploadForm.child_delimiter` | `child_delimiter` | string\|null | 仅父子分段时有值 |
| `uploadForm.child_overlap` | `child_overlap` | int\|null | 仅父子分段时有值 |
| `uploadForm.child_max_tokens` | `child_max_tokens` | int\|null | 仅父子分段时有值 |

## 六、UI 交互说明

1. **按钮位置**：文件列表页面右上角，与「返回知识库列表」按钮在同一行
2. **对话框宽度**：600px
3. **父子分段字段**：仅当「分段模式」选择「父子分段」时显示，其他模式隐藏
4. **文件选择**：使用 `el-upload` 组件，`auto-upload=false`（手动触发上传），限制1个文件
5. **上传中状态**：按钮显示 loading，防止重复提交
6. **上传成功**：关闭对话框，重置表单，刷新文件列表，提示「文件上传成功，正在解析中...」

## 七、注意事项

1. `pre_rule` 后端期望字符串格式，多选用分号 `;` 拼接，无选择时传空字符串
2. 父子分段参数（`parent_mode` 等）在非父子分段模式下传 `null`
3. 文件上传到 OSS 后，必须拿到返回的 `file_key` 才能调用创建文件接口
4. `upload_file` 接口已移除 `knowledge_id` 参数，`knowledge_id` 仅在创建文件接口中作为 `dataset_id` 传递
