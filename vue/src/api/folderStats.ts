import { axiosInst } from '.'

/** 单个文件夹的统计结果项 */
export interface FolderCountItem {
  path: string
  count: number
}

/** POST /db/folder_count_scan 返回 */
export interface FolderCountScanResp {
  job_id: string
}

/** GET /db/folder_count_status 返回 */
export interface FolderCountStatusResp {
  job_id: string
  status: 'queued' | 'running' | 'done' | 'error'
  stage: string
  folder_path?: string
  scanned?: number
  counted?: number
  total?: number
  result?: FolderCountItem[]
  error?: string
}

/** GET /db/folder_count_result 返回 */
export interface FolderCountResultResp {
  root_path?: string
  result: FolderCountItem[]
  total: number
  counted_at: string | null
}

/** 启动后台统计 job，返回 job_id */
export const startScan = async (folder_path: string) => {
  const resp = await axiosInst.value.post('/db/folder_count_scan', { folder_path })
  return resp.data as FolderCountScanResp
}

/** 轮询统计进度 / 结果 */
export const getScanStatus = async (job_id: string) => {
  const resp = await axiosInst.value.get('/db/folder_count_status', { params: { job_id } })
  return resp.data as FolderCountStatusResp
}

/** 读表返回已存结果（页面进入时调，命中秒开） */
export const getResult = async (folder_path: string) => {
  const resp = await axiosInst.value.get('/db/folder_count_result', { params: { folder_path } })
  return resp.data as FolderCountResultResp
}
