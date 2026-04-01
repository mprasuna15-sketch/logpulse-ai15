import { NextResponse } from 'next/server';
import { promises as fs } from 'fs';
import path from 'path';
import { parseLogs } from '@/lib/logParser';
import { analyzeLogs } from '@/lib/analysis';

export async function GET() {
    try {
        // Locate the log file in the backend directory
        // process.cwd() is usually the root of the next app.
        const filePath = path.join(process.cwd(), '..', 'backend', 'shecareerslogs2.json');

        // Check if file exists
        try {
            await fs.access(filePath);
        } catch (e) {
            return NextResponse.json({ error: 'Log file not found at ' + filePath }, { status: 404 });
        }

        const fileContent = await fs.readFile(filePath, 'utf-8');
        const rawLogs = JSON.parse(fileContent);

        const parsed = parseLogs(rawLogs);
        const { stats, recentLogs } = analyzeLogs(parsed);

        return NextResponse.json({ stats, recentLogs, totalParsed: parsed.length });
    } catch (error) {
        console.error("Error processing logs:", error);
        return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
    }
}
