'use client'

import { useCallback, useState } from 'react'
import useSWRInfinite from 'swr/infinite'
import { useTranslation } from 'react-i18next'
import { RiFileTextLine } from '@remixicon/react'
import ApiDocCard from './api-doc-card'
import type { ApiDocsListResponse } from '@/models/api-docs'
import { fetchApiDocsList } from '@/service/api-docs'
import Input from '@/app/components/base/input'
import Empty from './empty'

const getKey = (
  pageIndex: number,
  previousPageData: ApiDocsListResponse,
) => {
  if (!pageIndex || previousPageData.has_more)
    return { url: 'api-docs', params: { page: pageIndex + 1, limit: 30 } }

  return null
}
const ApiDocsList = () => {
  const { t } = useTranslation()
  const [searchKeywords, setSearchKeywords] = useState('')

  const { data: apiDocsData, setSize, isLoading } = useSWRInfinite(
    getKey,
    fetchApiDocsList,
    { revalidateFirstPage: false },
  )

  const handleLoadmore = useCallback(() => {
    setSize(size => size + 1)
  }, [setSize])

  const apiDocs = apiDocsData?.flatMap(item => item.data) || []
  const hasMore = apiDocsData?.[apiDocsData.length - 1]?.has_more || false

  const filteredApiDocs = apiDocs.filter(doc =>
    doc.app_name.toLowerCase().includes(searchKeywords.toLowerCase())
    || doc.app_mode.toLowerCase().includes(searchKeywords.toLowerCase()),
  )

  return (
    <div className='flex h-full flex-col'>
      {/* Header */}
      <div className='flex flex-col gap-4 bg-background-body px-12 pb-4 pt-8'>
        <div className='flex items-center justify-between'>
          <div className='flex items-center gap-3'>
            <RiFileTextLine className='h-8 w-8 text-text-secondary' />
            <div>
              <h1 className='text-xl font-semibold text-text-primary'>
                {t('common.menus.apiDocs')}
              </h1>
              <p className='mt-1 text-sm text-text-secondary'>
                查看和管理应用的API文档，包括HTTP接口和MQ消息格式
              </p>
            </div>
          </div>
        </div>

        {/* Search */}
        <div className='flex items-center gap-4'>
          <div className='max-w-xs flex-1'>
            <Input
              placeholder='搜索应用名称或类型...'
              value={searchKeywords}
              onChange={e => setSearchKeywords(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className='flex-1 overflow-y-auto px-12'>
        {isLoading && apiDocs.length === 0 ? (
          <div className='flex h-32 items-center justify-center'>
            <div className='text-text-secondary'>加载中...</div>
          </div>
        ) : filteredApiDocs.length === 0 ? (
          <Empty />
        ) : (
          <>
            <div className='grid grid-cols-1 gap-4 py-6'>
              {filteredApiDocs.map(apiDoc => (
                <ApiDocCard
                  key={apiDoc.id}
                  apiDoc={apiDoc}
                />
              ))}
            </div>

            {hasMore && (
              <div className='flex justify-center py-8'>
                <button
                  onClick={handleLoadmore}
                  className='rounded-lg px-4 py-2 text-sm font-medium text-primary-600 transition-colors hover:bg-primary-50 hover:text-primary-700'
                >
                  加载更多
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export default ApiDocsList
