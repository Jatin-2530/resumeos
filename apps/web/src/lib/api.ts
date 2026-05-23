import axios from "axios";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL
    ? `${process.env.NEXT_PUBLIC_API_URL}/api/v1`
    : "/api/backend";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60_000,
  headers: {
    "Content-Type": "application/json",
  },
});
