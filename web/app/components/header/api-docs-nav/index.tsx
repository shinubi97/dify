'use client'

import { useTranslation } from 'react-i18next'
import Link from 'next/link'
import { useSelectedLayoutSegment } from 'next/navigation'
import {
  RiFileTextFill,
  RiFileTextLine,
} from '@remixicon/react'
import classNames from '@/utils/classnames'

type ApiDocsNavProps = {
  className?: string
}

const ApiDocsNav = ({
  className,
}: ApiDocsNavProps) => {
  const { t } = useTranslation()
  const selectedSegment = useSelectedLayoutSegment()
  const activated = selectedSegment === 'api-docs'

  return (
    <Link href="/api-docs" className={classNames(
      'group text-sm font-medium',
      activated && 'hover:bg-components-main-nav-nav-button-bg-active-hover bg-components-main-nav-nav-button-bg-active font-semibold shadow-md',
      activated ? 'text-components-main-nav-nav-button-text-active' : 'text-components-main-nav-nav-button-text hover:bg-components-main-nav-nav-button-bg-hover',
      className,
    )}>
      {
        activated
          ? <RiFileTextFill className='h-4 w-4' />
          : <RiFileTextLine className='h-4 w-4' />
      }
      <div className='ml-2 max-[1024px]:hidden'>
        {t('common.menus.apiDocs')}
      </div>
    </Link>
  )
}

export default ApiDocsNav
