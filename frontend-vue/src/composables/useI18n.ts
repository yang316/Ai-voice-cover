import { computed } from 'vue'
import { useAppStore } from '@/stores/app'

const translations = {
  zh: {
    // Header
    pageTitle: 'AI 语音翻唱',
    pageSubtitle: '用 AI 语音克隆技术翻唱任意歌曲',

    // Tabs
    tabCover: '翻唱',
    tabTts: '语音合成',
    tabTrain: '训练模型',

    // Upload
    uploadAudio: '上传音频',
    clickToUpload: '点击上传',
    dragAndDrop: '或拖放文件',
    supportedFormats: 'MP3, WAV, FLAC, OGG，最大 50MB',

    // Settings
    settings: '设置',
    voiceModel: '目标声音',
    computeBackend: '计算后端',
    pitchShift: '音调偏移',
    noiseReduction: '降噪',
    apiKey: 'API 密钥',
    apiKeyHint: '云端后端需要填写',
    apiKeyPlaceholder: '输入你的 API 密钥',
    gptSovitsUrl: 'GPT-SoVITS 服务地址',

    // Backends
    backendLocal: '本地 GPU',
    backendGptSovits: 'GPT-SoVITS',
    backendElevenLabs: 'ElevenLabs',
    backendFishAudio: 'Fish Audio',

    // Actions
    createCover: '开始翻唱',
    processing: '处理中…',
    download: '下载',
    newCover: '新建翻唱',
    uploadVoiceModel: '上传声音模型',
    generate: '生成',
    startTraining: '开始训练',
    reset: '重置',

    // Pipeline steps
    separating: '分离人声',
    converting: '转换声音',
    mixing: '混合音频',
    complete: '完成！',

    // Status
    result: '结果',
    checkingBackend: '检查后端状态…',
    backendOnline: '在线',
    backendOffline: '离线',

    // Voice models
    voiceModels: '声音模型',
    noVoiceModels: '暂无声音模型',
    addVoiceModel: '添加声音模型',
    importVoiceModel: '导入声音模型',
    name: '名称',
    description: '描述',
    descriptionOptional: '（可选）',

    // Tasks
    recentTasks: '最近任务',
    noTasks: '暂无任务',

    // TTS
    ttsTitle: '文字转语音',
    enterText: '输入文字',
    textPlaceholder: '输入要合成的文字...',
    selectVoice: '选择语音',
    speed: '语速',
    pitch: '音调',
    generateSpeech: '生成语音',

    // Training
    trainTitle: '训练语音模型',
    modelName: '模型名称',
    uploadTrainingAudio: '上传训练音频',
    trainingParams: '训练参数',
    epochs: '训练轮次',
    batchSize: '批次大小',
    trainingProgress: '训练进度',
    currentEpoch: '当前轮次',
    loss: '损失值',
    eta: '预计剩余',
    trainingHistory: '训练记录',

    // Messages
    uploadSuccess: '上传成功',
    uploadFailed: '上传失败',
    deleteSuccess: '删除成功',
    deleteFailed: '删除失败',
    coverCreated: '翻唱任务创建成功！',
    taskFailed: '任务失败',
    error: '错误',
    success: '成功',

    // Additional
    loadingVoices: '加载声音中',
    noVoices: '暂无可用声音',
    selectModel: '选择模型',
    backendOfflineMsg: '后端服务离线',
    noDescription: '无描述',
    delete: '删除',
    cancel: '取消',
    upload: '上传',
    selectFile: '选择文件',
  },
  en: {
    // Header
    pageTitle: 'AI Voice Cover',
    pageSubtitle: 'Transform any song with AI voice cloning',

    // Tabs
    tabCover: 'Cover',
    tabTts: 'TTS',
    tabTrain: 'Train',

    // Upload
    uploadAudio: 'Upload Audio',
    clickToUpload: 'Click to upload',
    dragAndDrop: 'or drag and drop',
    supportedFormats: 'MP3, WAV, FLAC, OGG up to 50MB',

    // Settings
    settings: 'Settings',
    voiceModel: 'Voice Model',
    computeBackend: 'Compute Backend',
    pitchShift: 'Pitch Shift',
    noiseReduction: 'Noise Reduction',
    apiKey: 'API Key',
    apiKeyHint: 'Required for cloud backends',
    apiKeyPlaceholder: 'Enter your API key',
    gptSovitsUrl: 'GPT-SoVITS URL',

    // Backends
    backendLocal: 'Local GPU',
    backendGptSovits: 'GPT-SoVITS',
    backendElevenLabs: 'ElevenLabs',
    backendFishAudio: 'Fish Audio',

    // Actions
    createCover: 'Create Cover',
    processing: 'Processing…',
    download: 'Download',
    newCover: 'New Cover',
    uploadVoiceModel: 'Upload Voice Model',
    generate: 'Generate',
    startTraining: 'Start Training',
    reset: 'Reset',

    // Pipeline steps
    separating: 'Separating',
    converting: 'Converting',
    mixing: 'Mixing',
    complete: 'Complete!',

    // Status
    result: 'Result',
    checkingBackend: 'Checking backend…',
    backendOnline: 'Online',
    backendOffline: 'Offline',

    // Voice models
    voiceModels: 'Voice Models',
    noVoiceModels: 'No voice models',
    addVoiceModel: 'Add Voice Model',
    importVoiceModel: 'Import Voice Model',
    name: 'Name',
    description: 'Description',
    descriptionOptional: '(optional)',

    // Tasks
    recentTasks: 'Recent Tasks',
    noTasks: 'No tasks yet',

    // TTS
    ttsTitle: 'Text to Speech',
    enterText: 'Enter Text',
    textPlaceholder: 'Enter text to synthesize...',
    selectVoice: 'Select Voice',
    speed: 'Speed',
    pitch: 'Pitch',
    generateSpeech: 'Generate Speech',

    // Training
    trainTitle: 'Train Voice Model',
    modelName: 'Model Name',
    uploadTrainingAudio: 'Upload Training Audio',
    trainingParams: 'Training Parameters',
    epochs: 'Epochs',
    batchSize: 'Batch Size',
    trainingProgress: 'Training Progress',
    currentEpoch: 'Current Epoch',
    loss: 'Loss',
    eta: 'ETA',
    trainingHistory: 'Training History',

    // Messages
    uploadSuccess: 'Upload successful',
    uploadFailed: 'Upload failed',
    deleteSuccess: 'Delete successful',
    deleteFailed: 'Delete failed',
    coverCreated: 'Cover created successfully!',
    taskFailed: 'Task failed',
    error: 'Error',
    success: 'Success',

    // Additional
    loadingVoices: 'Loading voices',
    noVoices: 'No voices available',
    selectModel: 'Select Model',
    backendOfflineMsg: 'Backend offline',
    noDescription: 'No description',
    delete: 'Delete',
    cancel: 'Cancel',
    upload: 'Upload',
    selectFile: 'Select File',
  },
}

export function useI18n() {
  const app = useAppStore()

  const t = computed(() => {
    return (key: keyof typeof translations.zh): string => {
      return translations[app.lang][key] || key
    }
  })

  return {
    t: t.value,
    lang: computed(() => app.lang),
    setLang: app.setLang,
  }
}
