<<<<<<< HEAD
# Assignment Marketplace Platform

A two-sided marketplace where wholesalers list assignable purchase contracts as timed auctions; verified investors bid with earnest-money pre-auth and closing timelines; and an embedded services network plugs in per-deal.

## Features

- Auction System: English, sealed-bid, and Dutch auctions with anti-sniping
- Escrow Management: Integrated escrow workflows with e-signature support
- Service Marketplace: Title companies, inspectors, contractors, and lenders
- Compliance: State-specific policy enforcement and regulatory compliance
- Real-time Bidding: WebSocket-powered live auction experience
- Multi-tenant Architecture: Organizations with role-based access control

## Tech Stack

- Frontend: Next.js 13+ (App Router), React, TypeScript
- Backend: NestJS, Prisma ORM, PostgreSQL
- Infrastructure: AWS (Terraform), Docker, GitHub Actions
- Real-time: Socket.IO for live auctions and notifications
- Payments: Stripe, Dwolla for ACH
- Documents: DocuSign/Dropbox Sign integration

## Getting Started

First, clone the repository:
git clone https://github.com/yourusername/assignment-marketplace.git
cd assignment-marketplace

Then install dependencies:
npm install

Start development:
npm run dev

## Project Structure

assignment-marketplace/
+-- apps/
¦   +-- web/              # Next.js frontend
¦   +-- api/              # NestJS backend
¦   +-- admin/            # Admin dashboard
+-- packages/
¦   +-- ui/               # Shared UI components
¦   +-- types/            # Shared TypeScript types
¦   +-- config/           # Shared configuration
¦   +-- utils/            # Shared utilities
+-- terraform/            # Infrastructure as Code
+-- docker/               # Docker configurations

## Development Workflow

1. Create feature branches from main
2. Implement functionality following the technical design
3. Write tests for new features
4. Create pull requests for review
5. Merge to main after approval

## Contributing

1. Fork the repository
2. Create your feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add amazing feature')
4. Push to the branch (git push origin feature/amazing-feature)
5. Open a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
=======
# assignment-marketplace
Two-sided marketplace for assignable purchase contracts
>>>>>>> 8b0f61f3579a7d56cc531be5d4f78f6036d8cd7f
