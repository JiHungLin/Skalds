import { useState } from 'react'
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  SortingState,
  flexRender,
  ColumnDef,
} from '@tanstack/react-table'
import { ChevronUpIcon, ChevronDownIcon } from '@heroicons/react/24/outline'
import { DataGridProps } from '../../types'

function DataGrid<T>({ 
  data, 
  columns, 
  loading = false, 
  pagination,
  onRowClick 
}: DataGridProps<T>) {
  const [sorting, setSorting] = useState<SortingState>([])

  // Convert our column format to TanStack Table format
  const tableColumns: ColumnDef<T>[] = columns.map(col => ({
    accessorKey: col.key as string,
    header: col.header,
    enableSorting: col.sortable ?? true,
    cell: ({ getValue, row }) => {
      const value = getValue()
      return col.render ? col.render(value, row.original) : String(value)
    }
  }))

  const table = useReactTable({
    data,
    columns: tableColumns,
    state: {
      sorting,
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  })

  if (loading) {
    return (
      <div className="card">
        <div className="animate-pulse">
          <div className="card-header">
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
          </div>
          <div className="card-content space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-4 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            {table.getHeaderGroups().map(headerGroup => (
              <tr key={headerGroup.id} className="border-b border-gray-200">
                {headerGroup.headers.map(header => (
                  <th
                    key={header.id}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={`flex items-center gap-2 ${
                          header.column.getCanSort() ? 'cursor-pointer select-none' : ''
                        }`}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                        {header.column.getCanSort() && (
                          <span className="flex flex-col">
                            <ChevronUpIcon 
                              className={`w-3 h-3 ${
                                header.column.getIsSorted() === 'asc' 
                                  ? 'text-primary-600' 
                                  : 'text-gray-400'
                              }`}
                            />
                            <ChevronDownIcon 
                              className={`w-3 h-3 -mt-1 ${
                                header.column.getIsSorted() === 'desc' 
                                  ? 'text-primary-600' 
                                  : 'text-gray-400'
                              }`}
                            />
                          </span>
                        )}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {table.getRowModel().rows.map(row => (
              <tr
                key={row.id}
                className={`hover:bg-gray-50 ${
                  onRowClick ? 'cursor-pointer' : ''
                }`}
                onClick={() => onRowClick?.(row.original)}
              >
                {row.getVisibleCells().map(cell => (
                  <td
                    key={cell.id}
                    className="px-6 py-4 whitespace-nowrap text-sm text-gray-900"
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pagination && (
        <div className="card-footer flex items-center justify-between">
          <div className="text-sm text-gray-700">
            Showing {((pagination.page - 1) * pagination.pageSize) + 1} to{' '}
            {Math.min(pagination.page * pagination.pageSize, pagination.total)} of{' '}
            {pagination.total} results
          </div>
          <div className="flex items-center gap-2">
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => pagination.onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
            >
              Previous
            </button>
            <span className="text-sm text-gray-700">
              Page {pagination.page} of {Math.ceil(pagination.total / pagination.pageSize)}
            </span>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => pagination.onPageChange(pagination.page + 1)}
              disabled={pagination.page >= Math.ceil(pagination.total / pagination.pageSize)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default DataGrid