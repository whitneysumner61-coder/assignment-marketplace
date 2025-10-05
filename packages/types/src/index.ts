// Shared TypeScript types for Assignment Marketplace

export type UserRole = 'wholesaler' | 'investor' | 'provider' | 'admin'

export interface User {
  id: string
  email: string
  name: string
  role: UserRole
}

export interface Property {
  id: string
  address: string
  city: string
  state: string
  zip: string
  price: number
}

export type ListingStatus = 'draft' | 'active' | 'closed' | 'under_contract'

export interface Listing {
  id: string
  propertyId: string
  sellerId: string
  reservePrice: number
  startDate: string // ISO date
  endDate: string // ISO date
  status: ListingStatus
}
