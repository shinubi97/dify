'use client'

import { RiFileTextLine } from '@remixicon/react'

const Empty = () => {
  // const { t } = useTranslation()

  return (
    <div className='flex h-96 flex-col items-center justify-center'>
      <div className='mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-background-default'>
        <RiFileTextLine className='h-8 w-8 text-text-tertiary' />
      </div>
      <div className='text-center'>
        <h3 className='mb-2 text-lg font-semibold text-text-primary'>
          暂无API文档
        </h3>
        <p className='max-w-md text-sm text-text-secondary'>
          当您发布工作流应用时，系统会自动生成对应的API文档。请先创建并发布一个工作流应用。
        </p>
      </div>
    </div>
  )
}

export default Empty
