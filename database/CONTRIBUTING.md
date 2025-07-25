# Contributing to Spending Transaction Monitor

Welcome to the Spending Transaction Monitor project! This guide will help you set up your development environment and get the database running locally.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Node.js** (v18 or higher) - [Download here](https://nodejs.org/)
- **npm** (comes with Node.js)
- **Podman Desktop** - [Download here](https://podman-desktop.io/)
- **Git** - [Download here](https://git-scm.com/downloads)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/RHEcosystemAppEng/spending-transaction-monitor
cd spending-transaction-monitor
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Set Up Database Environment

Choose one of the following database setup options:

#### Option A: Podman PostgreSQL (Recommended)

Start the database:

```bash
# Start PostgreSQL in background
podman-compose --file compose.yaml up --detach

# Verify database is running
podman-compose ps
```

#### Option B: Local PostgreSQL Installation

If you prefer to install PostgreSQL locally:

- **macOS**: `brew install postgresql && brew services start postgresql`
- **Ubuntu**: `sudo apt-get install postgresql postgresql-contrib`
- **Windows**: Download from [PostgreSQL official site](https://www.postgresql.org/download/windows/)

### 4. Environment Configuration

The `.env` file should already exist. Verify it contains:

```env
# Database connection URL for PostgreSQL
DATABASE_URL="postgresql://postgres:password@localhost:5432/spending_monitor"

# Application environment
NODE_ENV="development"
```

> **Note**: Adjust the DATABASE_URL if using different credentials or host.

### 5. Database Setup and Migration

```bash
# Generate Prisma client
npm run db:generate

# Create and apply database migrations
npm run db:migrate

# Verify migration status
npx prisma migrate status
```

### 6. Seed the Database

```bash
# Populate database with sample data
npm run db:seed
```

### 7. Verify Setup

```bash
# Test database connection
npm run dev

# View data in Prisma Studio (optional)
npm run db:studio
```

## 🗃️ Database Schema Overview

The database includes the following main entities:

- **Users**: Customer information, address, financial data, location tracking
- **Credit Cards**: Payment methods linked to users
- **Transactions**: Purchase history with merchant and location details
- **Alert Rules**: Configurable spending alerts with AI-driven patterns
- **Alert Notifications**: Notification logs and delivery tracking

## 📝 Available NPM Scripts

| Command | Description |
|---------|-------------|
| `npm run build` | Compile TypeScript to JavaScript |
| `npm run dev` | Run development server |
| `npm start` | Run production server |
| `npm run db:generate` | Generate Prisma client |
| `npm run db:migrate` | Create and apply database migrations |
| `npm run db:reset` | Reset database (⚠️ destroys all data) |
| `npm run db:studio` | Open Prisma Studio in browser |
| `npm run db:seed` | Populate database with sample data |

## 🔧 Development Workflow

### Making Schema Changes

1. **Modify the schema**: Edit `prisma/schema.prisma`
2. **Generate migration**: `npm run db:migrate`
3. **Update client**: `npm run db:generate`
4. **Test changes**: `npm run dev`

### Adding Sample Data

1. **Edit seed file**: Modify `src/seed.ts`
2. **Reset database**: `npm run db:reset`
3. **Apply migrations**: `npm run db:migrate`
4. **Seed data**: `npm run db:seed`

### Viewing Data

```bash
# Open Prisma Studio (web interface)
npm run db:studio

# Or use custom verification script
npx ts-node src/verify-user.ts
```

## 🚨 Troubleshooting

### Database Connection Issues

**Error**: `Can't reach database server at localhost:5432`

**Solutions**:

1. Ensure PostgreSQL is running: `podman ps`
2. Check DATABASE_URL in `.env` file
3. Verify port 5432 is not blocked by firewall

### Migration Errors

**Error**: `Database schema is not up to date`

**Solutions**:

1. Check migration status: `npx prisma migrate status`
2. Apply pending migrations: `npm run db:migrate`
3. If corrupted, reset: `npm run db:reset`

### Seed Data Conflicts

**Error**: `Unique constraint failed on email`

**Solutions**:

Reset database: `npm run db:reset` then `npm run db:seed`

### TypeScript Compilation Errors

**Error**: TypeScript compilation issues

**Solutions**:

1. Regenerate Prisma client: `npm run db:generate`
2. Check TypeScript config: `npx tsc --noEmit`
3. Restart TypeScript server in your IDE

## 🐳 Docker Commands Reference

```bash
# Start all services
podman-compose --file compose.yaml up --detach

# View logs
podman logs spending-monitor-db

# Stop services
podman-compose down

# Remove everything (including data)
podman-compose down -v && podman rm spending-monitor-db

# Restart specific service
podman-compose restart spending-monitor-db

# Access PostgreSQL shell
podman exec spending-monitor-db psql -U postgres -d spending_monitor
```

## 🔒 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:port/db` |
| `NODE_ENV` | Application environment | `development` |

## 📊 Database Indexes

The schema includes optimized indexes for:

- User email (unique)
- Transaction date and user ID
- Transaction merchant category
- Transaction amount
- Alert rule user ID and active status
- Address city and state
- Location consent status

## 🧪 Testing Your Setup

Run this verification checklist:

- [ ] Database starts successfully
- [ ] Migrations apply without errors
- [ ] Seed data creates sample records
- [ ] Prisma Studio opens and displays data
- [ ] TypeScript compiles without errors
- [ ] Development server starts

## 🤝 Contributing Guidelines

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/your-feature`
3. **Test** your changes thoroughly
4. **Commit** with clear messages: `git commit -m "Add: description"`
5. **Push** to your fork: `git push origin feature/your-feature`
6. **Submit** a pull request

## 📞 Need Help?

If you encounter issues not covered in this guide:

1. Check existing GitHub issues
2. Review Prisma documentation: [prisma.io/docs](https://prisma.io/docs)
3. Create a new issue with detailed error messages and steps to reproduce

---

Happy coding! 🚀