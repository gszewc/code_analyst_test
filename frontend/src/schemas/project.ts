import { z } from 'zod'

export const projectCreateSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .max(255, 'Name must be 255 characters or fewer')
    .regex(/^[a-zA-Z0-9_ -]+$/, 'Name may only contain letters, digits, spaces, _ and -'),
  description: z
    .string()
    .max(1000, 'Description must be 1 000 characters or fewer')
    .optional()
    .or(z.literal('')),
})

export const projectUpdateSchema = projectCreateSchema.partial()

export type ProjectCreateInput = z.infer<typeof projectCreateSchema>
export type ProjectUpdateInput = z.infer<typeof projectUpdateSchema>
