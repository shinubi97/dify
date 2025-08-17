import { get } from './base'
import type { ApiDocsListResponse } from '@/models/api-docs'

export const fetchApiDocsList = (params: {
  page: number
  limit: number
  app_id?: string
  app_mode?: string
  keyword?: string
  sort_by?: string
}) => {
  return get<ApiDocsListResponse>('app-api-docs', { params })
}

export const fetchApiDocDetail = (docId: string) => {
  return get(`app-api-docs/${docId}`)
}

export const fetchApiDocByApp = (appId: string) => {
  return get(`apps/${appId}/api-docs`)
}
