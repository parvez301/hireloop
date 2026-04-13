import type { FastifyReply, FastifyRequest, HookHandlerDoneFunction } from "fastify";

export function bearerAuth(expectedToken: string) {
  return function (req: FastifyRequest, reply: FastifyReply, done: HookHandlerDoneFunction) {
    const header = req.headers.authorization ?? "";
    if (!header.startsWith("Bearer ")) {
      reply.code(401).send({
        success: false,
        error: "UNAUTHORIZED",
        message: "Missing bearer token",
      });
      return;
    }
    const token = header.slice("Bearer ".length).trim();
    if (token !== expectedToken) {
      reply.code(401).send({
        success: false,
        error: "UNAUTHORIZED",
        message: "Invalid token",
      });
      return;
    }
    done();
  };
}
