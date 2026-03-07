import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, AlertCircle, CheckCircle, Download, Loader2, Building2, Calendar, DollarSign, Hash, X, FileSearch, Shield, Award, List, AlertTriangle } from 'lucide-react'
import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

function App() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('disqualification')

  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0])
      setError(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxSize: 50 * 1024 * 1024,
    multiple: false
  })

  const handleUpload = async () => {
    if (!file) return

    setUploading(true)
    setError(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      
      const { id } = response.data
      await analyzeDocument(id)
    } catch (err) {
      setError(err.response?.data?.detail || '上传失败，请重试')
      setUploading(false)
    }
  }

  const analyzeDocument = async (id) => {
    setAnalyzing(true)
    
    try {
      const response = await axios.post(`${API_URL}/analyze/${id}`)
      setResult(response.data.analysis)
    } catch (err) {
      setError(err.response?.data?.detail || '分析失败，请重试')
    } finally {
      setUploading(false)
      setAnalyzing(false)
    }
  }

  const downloadTemplate = async () => {
    if (!result?.id) return
    
    try {
      const response = await axios.get(`${API_URL}/template/${result.id}`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `投标文件模板_${result.project_info?.项目名称 || '未命名'}.docx`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err) {
      setError('下载失败，请重试')
    }
  }

  const downloadJSON = async () => {
    if (!result?.id) return
    
    try {
      const response = await axios.get(`${API_URL}/analysis/${result.id}/json`, {
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `分析结果_${result.id}.json`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (err) {
      setError('下载失败，请重试')
    }
  }

  const reset = () => {
    setFile(null)
    setResult(null)
    setError(null)
    setActiveTab('disqualification')
  }

  const getRiskColor = (riskLevel) => {
    if (riskLevel === '高' || riskLevel === 'fatal') return 'bg-red-100 text-red-700 border-red-200'
    if (riskLevel === '中' || riskLevel === 'serious') return 'bg-orange-100 text-orange-700 border-orange-200'
    return 'bg-yellow-100 text-yellow-700 border-yellow-200'
  }

  const getRiskIcon = (riskLevel) => {
    if (riskLevel === '高' || riskLevel === 'fatal') return <AlertTriangle className="w-4 h-4 text-red-600" />
    if (riskLevel === '中' || riskLevel === 'serious') return <AlertCircle className="w-4 h-4 text-orange-600" />
    return <AlertCircle className="w-4 h-4 text-yellow-600" />
  }

  // 渲染上传页面
  if (!result) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-12 px-4">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="text-center mb-10">
            <h1 className="text-4xl font-bold text-gray-900 mb-3">招投标助手 v1.1</h1>
            <p className="text-lg text-gray-600">智能招标文件分析 · 投标文件模板生成</p>
            <p className="text-sm text-gray-500 mt-2">Powered by Kimi K2.5</p>
          </div>

          {/* Upload Area */}
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                isDragActive 
                  ? 'border-blue-500 bg-blue-50' 
                  : 'border-gray-300 hover:border-gray-400'
              }`}
            >
              <input {...getInputProps()} />
              <Upload className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-xl text-gray-700 mb-2">
                {isDragActive ? '松开以上传文件' : '拖拽招标文件到此处'}
              </p>
              <p className="text-gray-500 mb-4">或点击选择文件</p>
              <p className="text-sm text-gray-400">支持 PDF、DOC、DOCX 格式，最大 50MB</p>
            </div>

            {file && (
              <div className="mt-6 p-4 bg-blue-50 rounded-lg flex items-center justify-between">
                <div className="flex items-center">
                  <FileText className="w-5 h-5 text-blue-600 mr-3" />
                  <div>
                    <p className="font-medium text-gray-900">{file.name}</p>
                    <p className="text-sm text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                </div>
                <button
                  onClick={() => setFile(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            )}

            {error && (
              <div className="mt-6 p-4 bg-red-50 rounded-lg flex items-center text-red-700">
                <AlertCircle className="w-5 h-5 mr-2" />
                {error}
              </div>
            )}

            <button
              onClick={handleUpload}
              disabled={!file || uploading || analyzing}
              className="w-full mt-6 py-4 bg-blue-600 text-white rounded-xl font-semibold text-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
            >
              {uploading ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> 上传中...</>
              ) : analyzing ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> AI 分析中...</>
              ) : (
                <><FileSearch className="w-5 h-5 mr-2" /> 开始分析</>
              )}
            </button>
          </div>

          {/* Features */}
          <div className="grid grid-cols-3 gap-6 mt-10">
            <div className="bg-white rounded-xl p-6 shadow-md text-center">
              <Shield className="w-10 h-10 text-red-500 mx-auto mb-3" />
              <h3 className="font-semibold text-gray-900">废标项识别</h3>
              <p className="text-sm text-gray-500 mt-1">精准提取所有可能导致废标的条款</p>
            </div>
            <div className="bg-white rounded-xl p-6 shadow-md text-center">
              <Award className="w-10 h-10 text-blue-500 mx-auto mb-3" />
              <h3 className="font-semibold text-gray-900">评分标准解析</h3>
              <p className="text-sm text-gray-500 mt-1">深度分析评分细则和得分要点</p>
            </div>
            <div className="bg-white rounded-xl p-6 shadow-md text-center">
              <FileText className="w-10 h-10 text-green-500 mx-auto mb-3" />
              <h3 className="font-semibold text-gray-900">模板生成</h3>
              <p className="text-sm text-gray-500 mt-1">动态生成符合要求的投标文件</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // 渲染结果页面
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center">
            <h1 className="text-xl font-bold text-gray-900">分析结果</h1>
            <span className="ml-4 px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
              分析完成
            </span>
          </div>
          <div className="flex gap-3">
            <button
              onClick={downloadJSON}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 border rounded-lg hover:bg-gray-50 transition-colors"
            >
              下载 JSON
            </button>
            <button
              onClick={downloadTemplate}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center"
            >
              <Download className="w-4 h-4 mr-2" />
              下载投标文件模板
            </button>
            <button
              onClick={reset}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 border rounded-lg hover:bg-gray-50 transition-colors"
            >
              分析新文件
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Project Info */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Building2 className="w-5 h-5 mr-2 text-blue-600" />
            项目基本信息
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">项目名称</p>
              <p className="font-medium">{result.project_info?.项目名称 || '未识别'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">项目编号</p>
              <p className="font-medium">{result.project_info?.项目编号 || '未识别'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">采购人</p>
              <p className="font-medium">{result.project_info?.采购人 || '未识别'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">预算金额</p>
              <p className="font-medium">{result.project_info?.预算金额 || '未识别'}</p>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-3 gap-6">
          {/* Sidebar */}
          <div className="col-span-1">
            <div className="bg-white rounded-xl shadow-sm overflow-hidden">
              <button
                onClick={() => setActiveTab('disqualification')}
                className={`w-full px-4 py-3 text-left flex items-center transition-colors ${
                  activeTab === 'disqualification' ? 'bg-red-50 text-red-700 border-l-4 border-red-500' : 'hover:bg-gray-50'
                }`}
              >
                <AlertTriangle className="w-5 h-5 mr-3" />
                <div>
                  <p className="font-medium">废标项清单</p>
                  <p className="text-xs opacity-70">{result.disqualification_items?.length || 0} 项</p>
                </div>
              </button>
              <button
                onClick={() => setActiveTab('scoring')}
                className={`w-full px-4 py-3 text-left flex items-center transition-colors ${
                  activeTab === 'scoring' ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-500' : 'hover:bg-gray-50'
                }`}
              >
                <Award className="w-5 h-5 mr-3" />
                <div>
                  <p className="font-medium">评分标准</p>
                  <p className="text-xs opacity-70">{result.scoring_criteria?.length || 0} 项</p>
                </div>
              </button>
              <button
                onClick={() => setActiveTab('technical')}
                className={`w-full px-4 py-3 text-left flex items-center transition-colors ${
                  activeTab === 'technical' ? 'bg-purple-50 text-purple-700 border-l-4 border-purple-500' : 'hover:bg-gray-50'
                }`}
              >
                <Hash className="w-5 h-5 mr-3" />
                <div>
                  <p className="font-medium">技术参数</p>
                  <p className="text-xs opacity-70">{result.technical_requirements?.length || 0} 项</p>
                </div>
              </button>
              <button
                onClick={() => setActiveTab('checklist')}
                className={`w-full px-4 py-3 text-left flex items-center transition-colors ${
                  activeTab === 'checklist' ? 'bg-green-50 text-green-700 border-l-4 border-green-500' : 'hover:bg-gray-50'
                }`}
              >
                <List className="w-5 h-5 mr-3" />
                <div>
                  <p className="font-medium">检查清单</p>
                  <p className="text-xs opacity-70">{result.checklists?.length || 0} 项</p>
                </div>
              </button>
            </div>

            {/* Notes */}
            {result.notes?.length > 0 && (
              <div className="bg-yellow-50 rounded-xl p-4 mt-4 border border-yellow-200">
                <h3 className="font-medium text-yellow-800 mb-2 flex items-center">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  注意事项
                </h3>
                <ul className="text-sm text-yellow-700 space-y-1">
                  {result.notes.map((note, idx) => (
                    <li key={idx}>• {note}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Content */}
          <div className="col-span-2">
            <div className="bg-white rounded-xl shadow-sm p-6">
              {/* Disqualification Items */}
              {activeTab === 'disqualification' && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <Shield className="w-5 h-5 mr-2 text-red-600" />
                    废标项清单
                    <span className="ml-2 text-sm font-normal text-gray-500">
                      （共 {result.disqualification_items?.length || 0} 项）
                    </span>
                  </h2>
                  <div className="space-y-3">
                    {result.disqualification_items?.map((item, idx) => (
                      <div key={idx} className={`p-4 rounded-lg border ${getRiskColor(item.risk_level)}`}>
                        <div className="flex items-start justify-between">
                          <div className="flex items-center">
                            {getRiskIcon(item.risk_level)}
                            <span className="ml-2 font-medium">{item.category}</span>
                          </div>
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            item.risk_level === '高' ? 'bg-red-200 text-red-800' : 
                            item.risk_level === '中' ? 'bg-orange-200 text-orange-800' : 
                            'bg-yellow-200 text-yellow-800'
                          }`}>
                            {item.risk_level}风险
                          </span>
                        </div>
                        <p className="mt-2 text-sm">{item.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Scoring Criteria */}
              {activeTab === 'scoring' && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <Award className="w-5 h-5 mr-2 text-blue-600" />
                    评分标准
                  </h2>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">评审因素</th>
                          <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">分值</th>
                          <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">评分细则</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y">
                        {result.scoring_criteria?.map((item, idx) => (
                          <tr key={idx} className="hover:bg-gray-50">
                            <td className="px-4 py-3">
                              <span className={`inline-block px-2 py-1 rounded text-xs ${
                                item.category === '价格分' ? 'bg-green-100 text-green-700' :
                                item.category === '技术分' ? 'bg-blue-100 text-blue-700' :
                                item.category === '商务分' ? 'bg-purple-100 text-purple-700' :
                                'bg-gray-100 text-gray-700'
                              }`}>
                                {item.category}
                              </span>
                              <p className="mt-1 font-medium">{item.factor}</p>
                            </td>
                            <td className="px-4 py-3 font-semibold text-blue-600">{item.score}</td>
                            <td className="px-4 py-3 text-sm text-gray-600">{item.criteria}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Technical Requirements */}
              {activeTab === 'technical' && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <Hash className="w-5 h-5 mr-2 text-purple-600" />
                    技术参数要求
                  </h2>
                  <div className="space-y-3">
                    {result.technical_requirements?.map((req, idx) => (
                      <div key={idx} className="p-4 border rounded-lg hover:bg-gray-50">
                        <div className="flex items-center justify-between">
                          <p className="font-medium">{req.param_name}</p>
                          <div className="flex gap-2">
                            {req.is_essential && (
                              <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs">★ 实质性</span>
                            )}
                            {req.is_important && (
                              <span className="px-2 py-1 bg-orange-100 text-orange-700 rounded text-xs">▲ 重要</span>
                            )}
                            {req.is_demo && (
                              <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs"># 演示</span>
                            )}
                          </div>
                        </div>
                        <p className="mt-2 text-sm text-gray-600">{req.requirement}</p>
                        {req.proof_required && (
                          <p className="mt-2 text-xs text-gray-500">
                            证明材料：{req.proof_required}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Checklist */}
              {activeTab === 'checklist' && (
                <div>
                  <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <List className="w-5 h-5 mr-2 text-green-600" />
                    投标文件检查清单
                  </h2>
                  <div className="space-y-2">
                    {result.checklists?.map((item, idx) => (
                      <div key={idx} className="flex items-center p-3 bg-gray-50 rounded-lg">
                        <input type="checkbox" className="w-4 h-4 mr-3" />
                        <span className="text-sm">{item}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
