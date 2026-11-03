/** Retry transient authentication failures without treating an outage as logout. */
export async function checkAuth<T>(
  request: () => Promise<T>,
  cancelled: () => boolean,
  wait: (ms: number) => Promise<unknown> = ms => new Promise(resolve => setTimeout(resolve, ms)),
): Promise<T> {
  const delays = [1000, 2000, 3000, 4000];
  for (let attempt = 0; ; attempt++) {
    if (cancelled()) throw new Error("Authentication check cancelled");
    try {
      return await request();
    } catch (error) {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 401 || status === 403 || attempt >= delays.length || cancelled()) throw error;
      await wait(delays[attempt]);
    }
  }
}
