export type ApiDoc = {
  id: string
  tenant_id: string
  app_id: string
  app_name: string
  app_description?: string
  app_icon?: string
  app_icon_background?: string
  app_mode: string
  workflow_id?: string
  api_key: string
  endpoints: string
  curl_examples?: string
  python_examples?: string
  inputs_schema?: any[]
  outputs_schema?: any
  mock_data?: any
  mq_info?: {
    topic: string
    tag: string
    example_message: any
  }
  created_at: string
  updated_at: string
  created_by?: string
  updated_by?: string
}

export type ApiDocsListResponse = {
  data: ApiDoc[]
  has_more: boolean
  limit: number
  page: number
  total: number
}
