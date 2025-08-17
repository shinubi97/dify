'use client'

import { useState } from 'react'
import {
  RiCheckLine,
  RiCodeLine,
  RiEyeLine,
  RiEyeOffLine,
  RiFileCopyLine,
  RiFileTextLine,
  RiTerminalBoxLine,
} from '@remixicon/react'
import type { ApiDoc } from '@/models/api-docs'
import { useToastContext } from '@/app/components/base/toast'

type ApiDocCardProps = {
  apiDoc: ApiDoc
  onUpdate?: () => void
}

const ApiDocCard = ({ apiDoc }: ApiDocCardProps) => {
  const { notify } = useToastContext()
  const [copiedItems, setCopiedItems] = useState<Record<string, boolean>>({})
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({})

  const copyToClipboard = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedItems(prev => ({ ...prev, [key]: true }))
      notify({ type: 'success', message: '已复制到剪贴板' })
      setTimeout(() => {
        setCopiedItems(prev => ({ ...prev, [key]: false }))
      }, 2000)
    }
 catch {
      notify({ type: 'error', message: '复制失败' })
    }
  }

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({ ...prev, [section]: !prev[section] }))
  }

  const renderCodeBlock = (code: string, key: string) => (
    <div className='relative mt-2 rounded-lg bg-gray-900 p-4'>
      <pre className='overflow-x-auto whitespace-pre-wrap text-sm text-green-400'>
        {code}
      </pre>
      <button
        onClick={() => copyToClipboard(code, key)}
        className='absolute right-2 top-2 rounded-md p-2 text-gray-400 transition-colors hover:bg-gray-700 hover:text-white'
      >
        {copiedItems[key] ? (
          <RiCheckLine className='h-4 w-4 text-green-400' />
        ) : (
          <RiFileCopyLine className='h-4 w-4' />
        )}
      </button>
    </div>
  )

  const formatJson = (obj: any) => JSON.stringify(obj, null, 2)

  return (
    <div className='border-border rounded-xl border bg-background-default p-6 shadow-sm transition-shadow hover:shadow-md'>
      {/* Header */}
      <div className='mb-6 flex items-start justify-between'>
        <div className='flex items-start gap-4'>
          <div className='flex h-12 w-12 items-center justify-center rounded-lg bg-primary-50'>
            <RiFileTextLine className='h-6 w-6 text-primary-600' />
          </div>
          <div>
            <h3 className='mb-1 text-lg font-semibold text-text-primary'>
              {apiDoc.app_name}
            </h3>
            <div className='flex items-center gap-2 text-sm text-text-secondary'>
              <span className='rounded-md bg-background-body px-2 py-1'>
                {apiDoc.app_mode}
              </span>
              <span>•</span>
              <span>{new Date(apiDoc.updated_at).toLocaleString('zh-CN')}</span>
            </div>
          </div>
        </div>

      </div>

      {/* Endpoint Info */}
      <div className='mb-6'>
        <div className='mb-2 flex items-center gap-2'>
          <span className='text-sm font-medium text-text-primary'>API端点：</span>
          <code className='rounded bg-background-body px-2 py-1 text-sm'>
            {apiDoc.endpoints}
          </code>
          <button
            onClick={() => copyToClipboard(apiDoc.endpoints, 'endpoint')}
            className='p-1 text-text-secondary hover:text-text-primary'
          >
            {copiedItems.endpoint ? (
              <RiCheckLine className='h-4 w-4 text-green-600' />
            ) : (
              <RiFileCopyLine className='h-4 w-4' />
            )}
          </button>
        </div>
        <div className='flex items-center gap-2'>
          <span className='text-sm font-medium text-text-primary'>API密钥：</span>
          <code className='rounded bg-background-body px-2 py-1 font-mono text-sm'>
            {apiDoc.api_key.substring(0, 12)}...
          </code>
          <button
            onClick={() => copyToClipboard(apiDoc.api_key, 'apikey')}
            className='p-1 text-text-secondary hover:text-text-primary'
          >
            {copiedItems.apikey ? (
              <RiCheckLine className='h-4 w-4 text-green-600' />
            ) : (
              <RiFileCopyLine className='h-4 w-4' />
            )}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className='space-y-4'>
        {/* cURL Example */}
        {apiDoc.curl_examples && (
          <div className='border-border rounded-lg border'>
            <button
              onClick={() => toggleSection('curl')}
              className='flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-background-body'
            >
              <div className='flex items-center gap-2'>
                <RiTerminalBoxLine className='h-5 w-5 text-text-secondary' />
                <span className='font-medium text-text-primary'>cURL 示例</span>
              </div>
              {expandedSections.curl ? (
                <RiEyeOffLine className='h-4 w-4 text-text-secondary' />
              ) : (
                <RiEyeLine className='h-4 w-4 text-text-secondary' />
              )}
            </button>
            {expandedSections.curl && (
              <div className='px-4 pb-4'>
                {renderCodeBlock(apiDoc.curl_examples, 'curl')}
              </div>
            )}
          </div>
        )}

        {/* Python Example */}
        {apiDoc.python_examples && (
          <div className='border-border rounded-lg border'>
            <button
              onClick={() => toggleSection('python')}
              className='flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-background-body'
            >
              <div className='flex items-center gap-2'>
                <RiCodeLine className='h-5 w-5 text-text-secondary' />
                <span className='font-medium text-text-primary'>Python 示例</span>
              </div>
              {expandedSections.python ? (
                <RiEyeOffLine className='h-4 w-4 text-text-secondary' />
              ) : (
                <RiEyeLine className='h-4 w-4 text-text-secondary' />
              )}
            </button>
            {expandedSections.python && (
              <div className='px-4 pb-4'>
                {renderCodeBlock(apiDoc.python_examples, 'python')}
              </div>
            )}
          </div>
        )}

        {/* MQ Information */}
        {apiDoc.mq_info && (
          <div className='border-border rounded-lg border'>
            <button
              onClick={() => toggleSection('mq')}
              className='flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-background-body'
            >
              <div className='flex items-center gap-2'>
                <RiTerminalBoxLine className='h-5 w-5 text-text-secondary' />
                <span className='font-medium text-text-primary'>MQ 示例</span>
              </div>
              {expandedSections.mq ? (
                <RiEyeOffLine className='h-4 w-4 text-text-secondary' />
              ) : (
                <RiEyeLine className='h-4 w-4 text-text-secondary' />
              )}
            </button>
            {expandedSections.mq && (
              <div className='px-4 pb-4'>
                <div className='mt-2 grid grid-cols-1 gap-4 md:grid-cols-2'>
                  <div>
                    <h4 className='mb-2 text-sm font-medium text-text-primary'>主题和标签</h4>
                    <div className='space-y-1 text-sm'>
                      <div>Topic: <code className='rounded bg-background-body px-1'>{apiDoc.mq_info.topic}</code></div>
                      <div>Tag: <code className='rounded bg-background-body px-1'>{apiDoc.mq_info.tag}</code></div>
                    </div>
                  </div>
                  <div>
                    <h4 className='mb-2 text-sm font-medium text-text-primary'>示例消息</h4>
                    {renderCodeBlock(formatJson(apiDoc.mq_info.example_message), 'mq')}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ApiDocCard
