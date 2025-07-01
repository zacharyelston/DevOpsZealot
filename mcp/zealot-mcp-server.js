#!/usr/bin/env node
/**
 * MCP Server for DevOpsZealot
 * Allows Continue.dev to interact with DevOpsZealot
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ErrorCode,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  ListPromptsRequestSchema,
  McpError,
  ReadResourceRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';

const ZEALOT_API_URL = process.env.ZEALOT_API_URL || 'http://localhost:8080';

class DevOpsZealotMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'devops-zealot',
        version: '1.0.0',
      },
      {
        capabilities: {
          resources: {},
          tools: {},
          prompts: {},
        },
      }
    );

    this.setupHandlers();
  }

  setupHandlers() {
    // Resources handler
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => ({
      resources: [
        {
          uri: 'zealot://tasks/active',
          name: 'Active Tasks',
          description: 'List of currently active DevOpsZealot tasks',
        },
        {
          uri: 'zealot://tasks/history',
          name: 'Task History',
          description: 'Historical task execution data',
        },
        {
          uri: 'zealot://templates/infrastructure',
          name: 'Infrastructure Templates',
          description: 'Pre-configured infrastructure patterns',
        },
        {
          uri: 'zealot://validation/rules',
          name: 'Validation Rules',
          description: 'Available validation rules and their configurations',
        },
      ],
    }));

    // Read resource handler
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const { uri } = request.params;

      try {
        const response = await axios.get(`${ZEALOT_API_URL}/mcp/resource`, {
          params: { uri },
        });

        return {
          contents: [
            {
              uri,
              mimeType: 'application/json',
              text: JSON.stringify(response.data, null, 2),
            },
          ],
        };
      } catch (error) {
        throw new McpError(
          ErrorCode.InternalError,
          `Failed to fetch resource: ${error.message}`
        );
      }
    });

    // Tools handler
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'create_infrastructure_task',
          description: 'Create a new infrastructure editing task',
          inputSchema: {
            type: 'object',
            properties: {
              repository: {
                type: 'string',
                description: 'Git repository URL',
              },
              branch: {
                type: 'string',
                description: 'Target branch',
                default: 'main',
              },
              files: {
                type: 'array',
                items: { type: 'string' },
                description: 'Files to edit',
              },
              requirements: {
                type: 'array',
                items: { type: 'string' },
                description: 'Requirements for the changes',
              },
              validation_rules: {
                type: 'array',
                items: { type: 'string' },
                description: 'Validation rules to apply',
                default: ['terraform_validate', 'security_scan'],
              },
            },
            required: ['repository', 'files', 'requirements'],
          },
        },
        {
          name: 'validate_infrastructure_code',
          description: 'Validate infrastructure code without creating a task',
          inputSchema: {
            type: 'object',
            properties: {
              content: {
                type: 'string',
                description: 'Code content to validate',
              },
              file_type: {
                type: 'string',
                description: 'Type of file (terraform, yaml, etc.)',
              },
              rules: {
                type: 'array',
                items: { type: 'string' },
                description: 'Validation rules to apply',
              },
            },
            required: ['content', 'file_type'],
          },
        },
        {
          name: 'get_task_status',
          description: 'Get the status of a DevOpsZealot task',
          inputSchema: {
            type: 'object',
            properties: {
              task_id: {
                type: 'string',
                description: 'Task ID to check',
              },
            },
            required: ['task_id'],
          },
        },
      ],
    }));

    // Call tool handler
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        const response = await axios.post(`${ZEALOT_API_URL}/mcp/tool`, {
          tool: name,
          parameters: args,
        });

        return {
          content: [
            {
              type: 'text',
              text: JSON.stringify(response.data, null, 2),
            },
          ],
        };
      } catch (error) {
        throw new McpError(
          ErrorCode.InternalError,
          `Tool execution failed: ${error.message}`
        );
      }
    });

    // Prompts handler
    this.server.setRequestHandler(ListPromptsRequestSchema, async () => ({
      prompts: [
        {
          name: 'terraform_security_hardening',
          description: 'Harden Terraform configurations for security',
          arguments: [
            {
              name: 'code',
              description: 'Current Terraform configuration',
              required: true,
            },
            {
              name: 'environment',
              description: 'Target environment (dev/staging/prod)',
              required: true,
            },
            {
              name: 'compliance_standards',
              description: 'Compliance requirements (PCI, HIPAA, etc.)',
              required: false,
            },
          ],
        },
        {
          name: 'kubernetes_resource_optimization',
          description: 'Optimize Kubernetes resource allocations',
          arguments: [
            {
              name: 'manifest',
              description: 'Current Kubernetes manifest',
              required: true,
            },
            {
              name: 'cloud_provider',
              description: 'Cloud provider (aws/gcp/azure)',
              required: true,
            },
            {
              name: 'node_types',
              description: 'Available node types',
              required: false,
            },
            {
              name: 'utilization_metrics',
              description: 'Current resource utilization',
              required: false,
            },
          ],
        },
      ],
    }));
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('DevOpsZealot MCP Server running');
  }
}

// Run the server
const server = new DevOpsZealotMCPServer();
server.run().catch(console.error);
