'use client'

import { useTranslation } from 'react-i18next'
import useDocumentTitle from '@/hooks/use-document-title'
import ApiDocsList from './list'

const ApiDocs = () => {
  const { t } = useTranslation()

  useDocumentTitle(t('common.menus.apiDocs'))

  return (
    <div className='relative flex h-0 shrink-0 grow flex-col overflow-y-auto bg-background-body'>
      <ApiDocsList />
    </div>
  )
}

export default ApiDocs
