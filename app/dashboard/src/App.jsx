import React, { useState } from 'react'
import axios from 'axios'
import './index.css'

const API_BASE_URL = '/api/v1'
const API_KEY = import.meta.env.VITE_API_KEY || ''

function App() {
  const [activeTab, setActiveTab] = useState('upload')
  const [file, setFile] = useState(null)
  const [lang, setLang] = useState('en')
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [jobs, setJobs] = useState([])
  const [stats, setStats] = useState(null)
  
  // 상세 정보 모달 상태
  const [selectedJobId, setSelectedJobId] = useState(null)
  const [jobDetail, setJobDetail] = useState(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [detailError, setDetailError] = useState(null)

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
    setError(null)
  }

  const handleUpload = async () => {
    if (!file) {
      setError('파일을 선택해주세요')
      return
    }

    setProcessing(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('lang', lang)

      if (!API_KEY) {
        setError('API 키가 설정되지 않았습니다. VITE_API_KEY 환경 변수를 설정해주세요.')
        setProcessing(false)
        return
      }

      const response = await axios.post(`${API_BASE_URL}/get`, formData, {
        headers: {
          'Authorization': API_KEY,
        },
      })

      setResult(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || '오류가 발생했습니다')
    } finally {
      setProcessing(false)
    }
  }

  const loadJobs = async () => {
    if (!API_KEY) {
      console.error('API 키가 설정되지 않았습니다.')
      return
    }
    try {
      const response = await axios.get(`${API_BASE_URL}/jobs`, {
        headers: {
          'Authorization': API_KEY,
        },
      })
      setJobs(response.data)
    } catch (err) {
      console.error('작업 목록 로드 실패:', err)
    }
  }

  const loadStats = async () => {
    if (!API_KEY) {
      console.error('API 키가 설정되지 않았습니다.')
      return
    }
    try {
      const response = await axios.get(`${API_BASE_URL}/stats`, {
        headers: {
          'Authorization': API_KEY,
        },
      })
      setStats(response.data)
    } catch (err) {
      console.error('통계 로드 실패:', err)
    }
  }

  const loadJobDetail = async (id) => {
    setSelectedJobId(id)
    setLoadingDetail(true)
    setJobDetail(null)
    setDetailError(null)
    
    try {
      const response = await axios.get(`${API_BASE_URL}/result/${id}`, {
        headers: {
          'Authorization': API_KEY,
        },
      })
      setJobDetail(response.data)
    } catch (err) {
      console.error('상세 정보 로드 실패:', err)
      if (err.response?.status === 202) {
        setDetailError("작업이 아직 진행 중입니다.")
      } else {
        setDetailError(err.response?.data?.detail || "결과를 불러오는 데 실패했습니다.")
      }
    } finally {
      setLoadingDetail(false)
    }
  }

  const closeDetailModal = () => {
    setSelectedJobId(null)
    setJobDetail(null)
    setDetailError(null)
  }

  React.useEffect(() => {
    if (activeTab === 'jobs') {
      loadJobs()
    } else if (activeTab === 'stats') {
      loadStats()
    }
  }, [activeTab])

  return (
    <div className="container">
      <div className="header">
        <h1>의료 문서 OCR 시스템</h1>
        <nav className="nav">
          <a
            href="#"
            className={activeTab === 'upload' ? 'active' : ''}
            onClick={(e) => {
              e.preventDefault()
              setActiveTab('upload')
            }}
          >
            업로드
          </a>
          <a
            href="#"
            className={activeTab === 'jobs' ? 'active' : ''}
            onClick={(e) => {
              e.preventDefault()
              setActiveTab('jobs')
            }}
          >
            작업 목록
          </a>
          <a
            href="#"
            className={activeTab === 'stats' ? 'active' : ''}
            onClick={(e) => {
              e.preventDefault()
              setActiveTab('stats')
            }}
          >
            통계
          </a>
        </nav>
      </div>

      {activeTab === 'upload' && (
        <div className="card">
          <h2>파일 업로드</h2>
          <div>
            <input
              type="file"
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={handleFileChange}
              className="input"
            />
            <div style={{ marginTop: '10px', marginBottom: '10px' }}>
              <label htmlFor="lang-select" style={{ display: 'block', marginBottom: '5px', color: '#666' }}>
                언어 선택:
              </label>
              <select
                id="lang-select"
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                style={{
                  padding: '8px',
                  fontSize: '14px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  width: '200px',
                }}
              >
                <option value="en">영어 (English)</option>
                <option value="ko">한국어 (Korean)</option>
              </select>
            </div>
            <button
              onClick={handleUpload}
              disabled={processing || !file}
              className="button"
            >
              {processing ? '처리 중...' : '업로드 및 처리'}
            </button>
          </div>

          {error && (
            <div style={{ color: 'red', marginTop: '10px' }}>
              {error}
            </div>
          )}

          {result && (
            <div style={{ marginTop: '20px' }}>
              <h3>결과</h3>
              <div>
                <p>페이지 수: {result.pages.length}</p>
                {result.pages.map((page, idx) => (
                  <div key={idx} style={{ marginTop: '20px', border: '1px solid #ddd', padding: '10px' }}>
                    <h4>페이지 {page.page_index + 1}</h4>
                    <p>크기: {page.width} x {page.height}</p>
                    <p>아이템 수: {page.items.length}</p>
                    <div style={{ maxHeight: '300px', overflow: 'auto' }}>
                      {page.items.map((item, itemIdx) => (
                        <div
                          key={itemIdx}
                          style={{
                            margin: '5px 0',
                            padding: '5px',
                            backgroundColor: item.is_sensitive ? '#ffe6e6' : '#f0f0f0',
                          }}
                        >
                          <strong>{item.is_sensitive ? item.masked_text || item.text : item.text}</strong>
                          <span style={{ marginLeft: '10px', fontSize: '12px', color: '#666' }}>
                            ({item.bbox.x}, {item.bbox.y}) - 신뢰도: {(item.confidence * 100).toFixed(1)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'jobs' && (
        <div className="card">
          <h2>작업 목록</h2>
          <button onClick={loadJobs} className="button" style={{ marginBottom: '20px' }}>
            새로고침
          </button>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>파일명</th>
                <th>언어</th>
                <th>상태</th>
                <th>페이지 수</th>
                <th>생성 시간</th>
                <th>완료 시간</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => {
                const isClickable = job.status === 'done' || job.status === 'failed';
                return (
                  <tr key={job.id}>
                    <td 
                      onClick={() => isClickable && loadJobDetail(job.id)}
                      style={{ 
                        cursor: isClickable ? 'pointer' : 'default', 
                        color: isClickable ? '#3498db' : 'inherit', 
                        textDecoration: isClickable ? 'underline' : 'none' 
                      }}
                      title={isClickable ? "클릭하여 상세 정보 조회" : "처리 중인 작업입니다"}
                    >
                      {job.id.slice(0, 8)}...
                    </td>
                    <td>{job.filename}</td>
                    <td>{job.lang}</td>
                    <td>
                      <span className={`status ${job.status}`}>
                        {job.status}
                      </span>
                    </td>
                    <td>{job.page_count}</td>
                    <td>{new Date(job.created_at).toLocaleString('ko-KR')}</td>
                    <td>
                      {job.completed_at
                        ? new Date(job.completed_at).toLocaleString('ko-KR')
                        : '-'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'stats' && (
        <div className="card">
          <h2>통계</h2>
          <button onClick={loadStats} className="button" style={{ marginBottom: '20px' }}>
            새로고침
          </button>
          {stats && (
            <div>
              <p>총 작업 수: {stats.total_jobs}</p>
              <p>완료: {stats.completed_jobs}</p>
              <p>실패: {stats.failed_jobs}</p>
              <p>처리 중: {stats.processing_jobs}</p>
              {stats.avg_processing_time && (
                <p>평균 처리 시간: {stats.avg_processing_time.toFixed(2)}초</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* 상세 정보 모달 */}
      {selectedJobId && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }} onClick={closeDetailModal}>
          <div style={{
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '8px',
            width: '80%',
            maxWidth: '800px',
            maxHeight: '90vh',
            overflow: 'auto',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
          }} onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h3 style={{ margin: 0 }}>작업 상세 정보</h3>
              <button onClick={closeDetailModal} className="button" style={{ padding: '5px 10px', fontSize: '14px' }}>닫기</button>
            </div>
            
            <p><strong>Job ID:</strong> {selectedJobId}</p>
            
            {loadingDetail && <p>로딩 중...</p>}
            
            {detailError && <p style={{ color: 'red' }}>{detailError}</p>}
            
            {jobDetail && (
              <div>
                <p><strong>총 페이지 수:</strong> {jobDetail.pages.length}</p>
                {jobDetail.pages.map((page, idx) => (
                  <div key={idx} style={{ marginTop: '20px', borderTop: '1px solid #eee', paddingTop: '10px' }}>
                    <h4>Page {page.page_index + 1}</h4>
                    <p style={{ fontSize: '12px', color: '#666' }}>크기: {page.width} x {page.height}</p>
                    <div style={{ maxHeight: '300px', overflow: 'auto', background: '#f9f9f9', padding: '10px', borderRadius: '4px' }}>
                      {page.items.length === 0 ? (
                        <p style={{ color: '#999', fontStyle: 'italic' }}>텍스트 없음</p>
                      ) : (
                        page.items.map((item, itemIdx) => (
                          <div key={itemIdx} style={{ 
                            marginBottom: '5px', 
                            fontSize: '14px',
                            padding: '4px',
                            backgroundColor: item.is_sensitive ? '#ffe6e6' : 'transparent',
                            borderRadius: '2px'
                          }}>
                            <span style={{ fontWeight: 'bold' }}>
                              {item.is_sensitive ? (item.masked_text || '***') : item.text}
                            </span>
                            <span style={{ marginLeft: '8px', color: '#888', fontSize: '12px' }}>
                              (conf: {(item.confidence * 100).toFixed(0)}%)
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default App

