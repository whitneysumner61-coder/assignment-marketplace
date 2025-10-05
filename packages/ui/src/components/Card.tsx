import React from 'react'

export type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  children: React.ReactNode
}

const Card: React.FC<CardProps> = ({ children, className = '', ...rest }) => {
  return (
    <div className={`bg-white rounded shadow p-4 ${className}`} {...rest}>
      {children}
    </div>
  )
}

export default Card
