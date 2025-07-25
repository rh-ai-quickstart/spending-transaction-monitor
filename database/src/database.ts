import { PrismaClient } from '../generated/prisma';

// Initialize Prisma Client
const prisma = new PrismaClient({
  log: ['query', 'info', 'warn', 'error'],
});

// Handle graceful shutdown
process.on('beforeExit', async () => {
  await prisma.$disconnect();
});

export { prisma };
export default prisma; 